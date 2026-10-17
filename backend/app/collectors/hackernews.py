"""Hacker News vía Algolia HN Search API (pública, sin key).

Usamos `search_by_date` con un filtro de fecha, así cada ejecución trae también los puntos y
comentarios actuales de las stories recientes: re-ejecutar = nuevo snapshot.
"""

from datetime import UTC, datetime, timedelta

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.collectors.text import clean_html, is_ai_related
from app.collectors.usage import UsageMeter
from app.models import Source
from app.schemas.cost import Provider
from app.schemas.signal import ContentFormat, ContentSignal, Metrics, Platform

API_URL = "https://hn.algolia.com/api/v1/search_by_date"
ITEM_URL = "https://news.ycombinator.com/item?id={}"
MIN_POINTS = 3  # descarta stories sin ninguna tracción
HITS_PER_PAGE = 100
MAX_PAGES = 10


class HackerNewsCollector:
    def __init__(self, client: httpx.AsyncClient, usage: UsageMeter | None = None):
        self._http = client
        self.usage = usage or UsageMeter()

    @retry(
        retry=retry_if_exception_type(httpx.TransportError | httpx.HTTPStatusError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
    )
    async def _page(self, query: str, since: datetime, page: int) -> dict:
        r = await self._http.get(
            API_URL,
            params={
                "query": query,
                "tags": "story",
                "numericFilters": f"created_at_i>{int(since.timestamp())},points>={MIN_POINTS}",
                "hitsPerPage": HITS_PER_PAGE,
                "page": page,
            },
        )
        self.usage.add(Provider.HACKERNEWS, "search_by_date")
        r.raise_for_status()
        return r.json()

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]:
        observed_at = datetime.now(UTC)
        since = observed_at - timedelta(days=backfill_days)
        ai_filter = source.config.get("ai_filter", False)

        signals: list[ContentSignal] = []
        for page in range(MAX_PAGES):
            data = await self._page(source.external_id, since, page)
            for hit in data.get("hits", []):
                title = hit.get("title")
                if not title or (ai_filter and not is_ai_related(title, hit.get("story_text"))):
                    continue
                signals.append(
                    ContentSignal(
                        platform=Platform.HACKERNEWS,
                        external_id=hit["objectID"],
                        url=ITEM_URL.format(hit["objectID"]),
                        target_url=hit.get("url") or None,
                        title=title,
                        description=clean_html(hit.get("story_text")),
                        # El autor en HN es un particular: no se guarda (sin datos personales).
                        author_name=None,
                        published_at=datetime.fromtimestamp(hit["created_at_i"], UTC),
                        observed_at=observed_at,
                        format=ContentFormat.DISCUSSION,
                        language="en",
                        metrics=Metrics(points=hit.get("points"), comments=hit.get("num_comments")),
                    )
                )
            if page + 1 >= data.get("nbPages", 0):
                break
        return signals
