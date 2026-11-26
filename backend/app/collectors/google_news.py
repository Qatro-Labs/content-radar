"""Búsquedas de Google News por RSS: noticias de cualquier tema por idioma y país, sin clave.

Como RSS, no trae métricas: aporta cobertura (saturación, validación cruzada y brecha de región),
no velocidad por pieza. El enlace es el de Google News, que redirige a la nota del medio.
"""

from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import feedparser
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.collectors.rss import USER_AGENT, _entry_datetime, _external_id
from app.collectors.text import clean_html, is_ai_related
from app.collectors.usage import UsageMeter
from app.models import Source
from app.schemas.cost import Provider
from app.schemas.signal import ContentFormat, ContentSignal, Platform

SEARCH_URL = "https://news.google.com/rss/search"
# Comprobado el 26/11 contra el feed real: `ceid` conserva "es-419" (CO:es-419 trae notas,
# CO:es ninguna), pero en inglés solo vale el idioma (US:en sí, US:en-US no).
LATAM_SPANISH = "-419"


def google_news_feed_url(query: str, *, hl: str, gl: str, days: int) -> str:
    language = hl if hl.endswith(LATAM_SPANISH) else hl.split("-")[0]
    params = {"q": f"{query} when:{days}d", "hl": hl, "gl": gl, "ceid": f"{gl}:{language}"}
    return f"{SEARCH_URL}?{urlencode(params)}"


def _without_outlet(title: str, outlet: str | None) -> str:
    # Google News añade " - Medio" al título; sin quitarlo, la regla de mismo título no reconoce
    # la misma nota cuando también llega por el RSS del medio.
    suffix = f" - {outlet}" if outlet else None
    return title.removesuffix(suffix).strip() if suffix and title.endswith(suffix) else title


class GoogleNewsCollector:
    def __init__(self, client: httpx.AsyncClient, usage: UsageMeter | None = None):
        self._http = client
        self.usage = usage or UsageMeter()

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
    )
    async def _fetch(self, url: str) -> bytes:
        r = await self._http.get(url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
        self.usage.add(Provider.GOOGLE_NEWS, "feed")
        r.raise_for_status()
        return r.content

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]:
        observed_at = datetime.now(UTC)
        since = observed_at - timedelta(days=backfill_days)
        hl, gl = source.config["hl"], source.config["gl"]
        url = google_news_feed_url(source.config["query"], hl=hl, gl=gl, days=backfill_days)
        feed = feedparser.parse(await self._fetch(url))
        signals = [_entry_signal(e, source, observed_at, hl) for e in feed.entries]
        return [s for s in signals if s and s.published_at >= since]


def _entry_signal(entry, source: Source, observed_at: datetime, hl: str) -> ContentSignal | None:
    published_at = _entry_datetime(entry)
    link = entry.get("link")
    outlet = entry.get("source", {}).get("title")
    title = clean_html(entry.get("title"), max_length=500)
    if not (published_at and link and title):
        return None
    title = _without_outlet(title, outlet)
    if source.config.get("ai_filter", False) and not is_ai_related(title):
        return None
    return ContentSignal(
        platform=Platform.GOOGLE_NEWS,
        external_id=_external_id(entry, link),
        url=link,
        title=title,
        # La descripción del feed solo repite el título y el medio: no aporta.
        description=None,
        author_name=outlet,
        published_at=min(published_at, observed_at),
        observed_at=observed_at,
        format=ContentFormat.ARTICLE,
        language=hl[:2],
    )
