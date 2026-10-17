"""Feeds RSS/Atom de medios y blogs. No traen métricas: aportan cobertura (saturación,
validación cruzada y LATAM Gap), no velocidad por pieza."""

import calendar
import hashlib
from datetime import UTC, datetime, timedelta

import feedparser
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.collectors.text import clean_html, is_ai_related
from app.models import Source
from app.schemas.signal import ContentFormat, ContentSignal, Platform

USER_AGENT = (
    "Mozilla/5.0 (compatible; content-radar/0.1; +https://github.com/Qatro-Labs/content-radar)"
)


def _external_id(entry, link: str) -> str:
    value = entry.get("id") or link
    # La columna admite 512; algunos feeds usan URLs larguísimas como guid.
    return value if len(value) <= 512 else hashlib.sha256(value.encode()).hexdigest()


def _entry_datetime(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime.fromtimestamp(calendar.timegm(parsed), UTC) if parsed else None


class RSSCollector:
    def __init__(self, client: httpx.AsyncClient):
        self._http = client

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
    )
    async def _fetch(self, url: str) -> bytes:
        r = await self._http.get(url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
        r.raise_for_status()
        return r.content

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]:
        observed_at = datetime.now(UTC)
        since = observed_at - timedelta(days=backfill_days)
        ai_filter = source.config.get("ai_filter", False)

        feed = feedparser.parse(await self._fetch(source.external_id))
        signals: list[ContentSignal] = []
        for entry in feed.entries:
            published_at = _entry_datetime(entry)
            link = entry.get("link")
            title = clean_html(entry.get("title"), max_length=500)
            if not (published_at and link and title) or published_at < since:
                continue
            summary = clean_html(entry.get("summary"))
            if ai_filter and not is_ai_related(title, summary):
                continue
            signals.append(
                ContentSignal(
                    platform=Platform.RSS,
                    external_id=_external_id(entry, link),
                    url=link,
                    title=title,
                    description=summary,
                    author_name=source.name,  # el medio, no el periodista
                    published_at=min(published_at, observed_at),
                    observed_at=observed_at,
                    format=ContentFormat.ARTICLE,
                    language=source.language,
                )
            )
        return signals
