"""TikTok y Reddit vía ScrapeCreators (proveedor de datos públicos, pago por crédito).

Coste: 1 crédito por llamada (también si la página viene vacía). Cada fuente hace una sola
llamada por ejecución, así que el gasto por ciclo = nº de fuentes activas de estas plataformas.

- TikTok: búsqueda por palabra clave de la última semana, opcionalmente por región.
- Reddit: posts top de la semana de un subreddit.

Re-ejecutar = nuevo snapshot de las piezas que sigan apareciendo.
"""

from datetime import UTC, datetime

import httpx
from pydantic import HttpUrl
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.collectors.text import is_ai_related
from app.collectors.usage import UsageMeter
from app.models import Source
from app.schemas.cost import Provider
from app.schemas.signal import ContentFormat, ContentSignal, Metrics, Platform

API_BASE = "https://api.scrapecreators.com"
TIKTOK_VIDEO_URL = "https://www.tiktok.com/@{}/video/{}"
REDDIT_POST_URL = "https://www.reddit.com/r/{}/comments/{}/"
# Enlaces de Reddit que apuntan a su propio contenido (imagen, vídeo, galería): no unen fuentes.
REDDIT_HOSTS = ("reddit.com", "redd.it")
MIN_TIKTOK_VIEWS = 100  # descarta spam y vídeos sin ninguna tracción
MIN_REDDIT_SCORE = 10
TITLE_CHARS = 140
DESCRIPTION_CHARS = 5000  # límite de ContentSignal.description


class ScrapeCreatorsClient:
    def __init__(self, api_key: str, client: httpx.AsyncClient, usage: UsageMeter):
        self._key = api_key
        self._http = client
        self.usage = usage

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
    )
    async def get(self, path: str, params: dict[str, str]) -> dict:
        r = await self._http.get(
            f"{API_BASE}{path}", params=params, headers={"x-api-key": self._key}
        )
        # Sin reintentar errores HTTP: un 402 (sin créditos) o 4xx no mejora y cada intento cuesta.
        self.usage.add(Provider.SCRAPECREATORS, path)
        r.raise_for_status()
        return r.json()


def _title(text: str) -> str:
    first_line = text.strip().split("\n", 1)[0]
    return first_line[:TITLE_CHARS] or text[:TITLE_CHARS]


class TikTokCollector:
    """`config.query` = palabra clave y `config.region` (ISO, p. ej. MX) el país de la búsqueda.
    `config.item_regions` descarta vídeos de otros países: la misma búsqueda desde México trae
    vídeos de España, que no cuentan para el LATAM Gap (CLAUDE.md §5).
    """

    def __init__(self, client: ScrapeCreatorsClient):
        self._api = client

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]:
        # La API solo filtra por periodos fijos; la semana cubre el ciclo periódico (--days 7).
        params = {"query": source.config["query"], "date_posted": "this-week", "trim": "true"}
        if region := source.config.get("region"):
            params["region"] = region
        data = await self._api.get("/v1/tiktok/search/keyword", params)

        observed_at = datetime.now(UTC)
        signals: dict[str, ContentSignal] = {}  # por id: TikTok repite resultados en una página
        for video in data.get("search_item_list") or []:
            if _keep_video(video, source.config) and video["aweme_id"] not in signals:
                signals[video["aweme_id"]] = _video_signal(video, source, observed_at)
        return list(signals.values())


def _keep_video(video: dict, config: dict) -> bool:
    item_regions = config.get("item_regions")
    desc = video.get("desc") or ""
    return bool(
        video.get("aweme_id")
        and (video.get("author") or {}).get("unique_id")
        and desc.strip()
        and not video.get("is_ad")
        and ((video.get("statistics") or {}).get("play_count") or 0) >= MIN_TIKTOK_VIEWS
        and (not item_regions or video.get("region") in item_regions)
        and (not config.get("ai_filter") or is_ai_related(desc))
    )


def _video_signal(video: dict, source: Source, observed_at: datetime) -> ContentSignal:
    stats = video.get("statistics") or {}
    desc = video["desc"].strip()
    handle = video["author"]["unique_id"]
    duration_ms = (video.get("video") or {}).get("duration")
    return ContentSignal(
        platform=Platform.TIKTOK,
        external_id=video["aweme_id"],
        url=HttpUrl(TIKTOK_VIDEO_URL.format(handle, video["aweme_id"])),
        title=_title(desc),
        description=desc[:DESCRIPTION_CHARS],
        # Cuenta pública que publica (como un canal de YouTube), no un usuario.
        author_name=f"@{handle}",
        published_at=datetime.fromtimestamp(video["create_time"], UTC),
        observed_at=observed_at,
        format=ContentFormat.SHORT_VIDEO,
        language=video.get("desc_language") or source.language,
        duration_seconds=round(duration_ms / 1000) if duration_ms else None,
        metrics=Metrics(
            views=stats.get("play_count"),
            likes=stats.get("digg_count"),
            comments=stats.get("comment_count"),
            shares=stats.get("share_count"),
        ),
    )


class RedditCollector:
    """`source.external_id` = nombre del subreddit (sin `r/`)."""

    def __init__(self, client: ScrapeCreatorsClient):
        self._api = client

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]:
        data = await self._api.get(
            "/v1/reddit/subreddit",
            {"subreddit": source.external_id, "sort": "top", "timeframe": "week", "trim": "true"},
        )
        observed_at = datetime.now(UTC)
        ai_filter = source.config.get("ai_filter", False)
        signals: list[ContentSignal] = []
        for post in data.get("posts") or []:
            title = (post.get("title") or "").strip()
            body = (post.get("selftext") or "").strip() or None
            if not (title and post.get("id")) or (post.get("score") or 0) < MIN_REDDIT_SCORE:
                continue
            if ai_filter and not is_ai_related(title, body):
                continue
            link = post.get("url") or ""
            external = link.startswith("http") and not any(h in link for h in REDDIT_HOSTS)
            subreddit = post.get("subreddit") or source.external_id
            signals.append(
                ContentSignal(
                    platform=Platform.REDDIT,
                    external_id=post["id"],
                    url=HttpUrl(REDDIT_POST_URL.format(subreddit, post["id"])),
                    target_url=HttpUrl(link) if external else None,
                    title=title,
                    description=body[:DESCRIPTION_CHARS] if body else None,
                    # El autor en Reddit es un particular: no se guarda (sin datos personales).
                    author_name=None,
                    published_at=datetime.fromtimestamp(post["created_utc"], UTC),
                    observed_at=observed_at,
                    format=ContentFormat.DISCUSSION,
                    language=source.language,
                    metrics=Metrics(points=post.get("score"), comments=post.get("num_comments")),
                )
            )
        return signals
