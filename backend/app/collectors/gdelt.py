"""GDELT DOC 2.0: noticias globales abiertas, con país e idioma de cada medio.

Sin clave y sin métricas: aporta cobertura, como RSS. Límite de la API: una petición cada 5 s
por cliente; si se pasa, responde 200 con un aviso en texto plano en vez de JSON.
https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""

import asyncio
import hashlib
import time
from datetime import UTC, datetime, timedelta

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.collectors.text import clean_html, is_ai_related
from app.collectors.usage import UsageMeter
from app.models import Source
from app.schemas.cost import Provider
from app.schemas.signal import ContentFormat, ContentSignal, Platform

API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_MIN_INTERVAL_SECONDS = 5
MAX_RECORDS = "250"
SEEN_DATE_FORMAT = "%Y%m%dT%H%M%SZ"
MAX_EXTERNAL_ID = 512
ERROR_TEXT_CHARS = 300
GDELT_LANGUAGE = {"Spanish": "es", "English": "en", "Portuguese": "pt"}


class GDELTError(Exception):
    pass


class GDELTCollector:
    def __init__(self, client: httpx.AsyncClient, usage: UsageMeter | None = None):
        self._http = client
        self.usage = usage or UsageMeter()
        # El job recolecta fuentes en paralelo: el lock reparte las peticiones en el tiempo.
        self._lock = asyncio.Lock()
        self._last_request: float | None = None

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]:
        observed_at = datetime.now(UTC)
        since = observed_at - timedelta(days=backfill_days)
        data = await self._paced_get(_params(source, backfill_days))
        signals = [_article_signal(a, source, observed_at) for a in data.get("articles", [])]
        return [s for s in signals if s and s.published_at >= since]

    async def _paced_get(self, params: dict[str, str]) -> dict:
        async with self._lock:
            if self._last_request is not None:
                wait = GDELT_MIN_INTERVAL_SECONDS - (time.monotonic() - self._last_request)
                if wait > 0:
                    await asyncio.sleep(wait)
            try:
                return await self._get(params)
            finally:
                self._last_request = time.monotonic()

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
    )
    async def _get(self, params: dict[str, str]) -> dict:
        r = await self._http.get(API_URL, params=params)
        self.usage.add(Provider.GDELT, "doc")
        if r.status_code != 200:
            raise GDELTError(f"HTTP {r.status_code}: {r.text[:ERROR_TEXT_CHARS]}")
        try:
            return r.json()
        except ValueError as e:
            # Consulta inválida o límite de peticiones: GDELT lo explica en texto plano.
            raise GDELTError(r.text[:ERROR_TEXT_CHARS].strip()) from e


def _params(source: Source, backfill_days: int) -> dict[str, str]:
    terms = [source.config["query"]]
    if country := source.config.get("source_country"):
        terms.append(f"sourcecountry:{country}")
    if lang := source.config.get("source_lang"):
        terms.append(f"sourcelang:{lang}")
    return {
        "query": " ".join(terms),
        "mode": "ArtList",
        "format": "json",
        "maxrecords": MAX_RECORDS,
        "timespan": f"{backfill_days}d",
        "sort": "DateDesc",
    }


def _article_signal(article: dict, source: Source, observed_at: datetime) -> ContentSignal | None:
    url, seen = article.get("url"), article.get("seendate")
    title = clean_html(article.get("title"), max_length=500)
    if not (url and seen and title):
        return None
    if source.config.get("ai_filter", False) and not is_ai_related(title):
        return None
    published_at = datetime.strptime(seen, SEEN_DATE_FORMAT).replace(tzinfo=UTC)
    return ContentSignal(
        platform=Platform.GDELT,
        external_id=url
        if len(url) <= MAX_EXTERNAL_ID
        else hashlib.sha256(url.encode()).hexdigest(),
        url=url,
        title=title,
        description=None,
        author_name=article.get("domain"),
        published_at=min(published_at, observed_at),
        observed_at=observed_at,
        format=ContentFormat.ARTICLE,
        language=GDELT_LANGUAGE.get(article.get("language", "")),
    )
