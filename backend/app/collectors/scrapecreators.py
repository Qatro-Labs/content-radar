"""TikTok, Reddit e Instagram vía ScrapeCreators (proveedor de datos públicos, pago por crédito).

Coste: 1 crédito por llamada (también si la página viene vacía). Cada fuente hace una sola
llamada por ejecución, así que el gasto por ciclo = nº de fuentes activas de estas plataformas.

- TikTok: búsqueda por palabra clave de la última semana, opcionalmente por región.
- Reddit: posts top de la semana de un subreddit.
- Instagram: últimos reels de un perfil, como un canal de YouTube (no hay búsqueda por tema fiable).

Re-ejecutar = nuevo snapshot de las piezas que sigan apareciendo.
"""

from datetime import UTC, datetime, timedelta

import httpx
from pydantic import HttpUrl
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.collectors.text import clean_html, headline, is_ai_related
from app.collectors.usage import UsageMeter
from app.models import Source
from app.schemas.cost import Provider
from app.schemas.signal import ContentFormat, ContentSignal, Metrics, Platform

API_BASE = "https://api.scrapecreators.com"
TIKTOK_VIDEO_URL = "https://www.tiktok.com/@{}/video/{}"
REDDIT_POST_URL = "https://www.reddit.com/r/{}/comments/{}/"
INSTAGRAM_REEL_URL = "https://www.instagram.com/reel/{}/"
# Enlaces de Reddit que apuntan a su propio contenido (imagen, vídeo, galería): no unen fuentes.
REDDIT_HOSTS = ("reddit.com", "redd.it")
MIN_TIKTOK_VIEWS = 100  # descarta spam y vídeos sin ninguna tracción
MIN_REDDIT_SCORE = 10


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
        # Sin reintentar errores HTTP: un 402 (sin créditos) o un 4xx no mejora reintentando.
        # Solo se cobran las respuestas correctas (los errores no gastan crédito, según sus docs).
        r.raise_for_status()
        self.usage.add(Provider.SCRAPECREATORS, path)
        return r.json()


class TikTokCollector:
    """`config.query` = palabra clave y `config.search_region` (ISO, p. ej. MX) el país de la
    búsqueda.
    `config.item_regions` descarta vídeos de otros países: la misma búsqueda desde México trae
    vídeos de España, que no cuentan para el LATAM Gap (CLAUDE.md §5).
    """

    def __init__(self, client: ScrapeCreatorsClient):
        self._api = client

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]:
        # La API solo filtra por periodos fijos; la semana cubre el ciclo periódico (--days 7).
        params = {"query": source.config["query"], "date_posted": "this-week", "trim": "true"}
        if search_region := source.config.get("search_region"):
            params["region"] = search_region
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
        title=headline(desc),
        description=clean_html(desc),
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
        return [
            _post_signal(post, source, observed_at)
            for post in data.get("posts") or []
            if _keep_post(post, ai_filter=ai_filter)
        ]


def _keep_post(post: dict, *, ai_filter: bool) -> bool:
    title = (post.get("title") or "").strip()
    return bool(
        title
        and post.get("id")
        and (post.get("score") or 0) >= MIN_REDDIT_SCORE
        and (not ai_filter or is_ai_related(title, post.get("selftext")))
    )


def _post_signal(post: dict, source: Source, observed_at: datetime) -> ContentSignal:
    link = post.get("url") or ""
    external = link.startswith("http") and not any(h in link for h in REDDIT_HOSTS)
    subreddit = post.get("subreddit") or source.external_id
    return ContentSignal(
        platform=Platform.REDDIT,
        external_id=post["id"],
        url=HttpUrl(REDDIT_POST_URL.format(subreddit, post["id"])),
        target_url=HttpUrl(link) if external else None,
        title=post["title"].strip(),
        # Texto de un particular: solo un extracto, como el de HN (sin copias completas).
        description=clean_html(post.get("selftext")),
        # El autor en Reddit es un particular: no se guarda (sin datos personales).
        author_name=None,
        published_at=datetime.fromtimestamp(post["created_utc"], UTC),
        observed_at=observed_at,
        format=ContentFormat.DISCUSSION,
        language=source.language,
        metrics=Metrics(points=post.get("score"), comments=post.get("num_comments")),
    )


class InstagramCollector:
    """`source.external_id` = handle del perfil (sin `@`).

    Usa el endpoint de reels y no el de posts: el de posts no trae views en todos los perfiles,
    y sin views no hay outlier.
    """

    def __init__(self, client: ScrapeCreatorsClient):
        self._api = client

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]:
        data = await self._api.get(
            "/v1/instagram/user/reels", {"handle": source.external_id, "trim": "true"}
        )
        observed_at = datetime.now(UTC)
        since = observed_at - timedelta(days=backfill_days)
        ai_filter = source.config.get("ai_filter", False)
        return [
            _reel_signal(reel, source, observed_at)
            for reel in data.get("items") or []
            if _keep_reel(reel, source.external_id, since, ai_filter=ai_filter)
        ]


def _caption(reel: dict) -> str:
    caption = reel.get("caption")
    text = caption.get("text") if isinstance(caption, dict) else caption
    return (text or "").strip()


def _keep_reel(reel: dict, handle: str, since: datetime, *, ai_filter: bool) -> bool:
    caption = _caption(reel)
    return bool(
        reel.get("code")
        and caption
        # Las colaboraciones de otras cuentas aparecen en el perfil, pero su rendimiento depende
        # de otra audiencia: compararlas con la mediana del perfil daría outliers falsos.
        and (reel.get("user") or {}).get("username") == handle
        and reel.get("play_count") is not None
        # Los reels fijados llegan primero aunque tengan meses.
        and datetime.fromtimestamp(reel.get("taken_at") or 0, UTC) >= since
        and (not ai_filter or is_ai_related(caption))
    )


def _reel_signal(reel: dict, source: Source, observed_at: datetime) -> ContentSignal:
    caption = _caption(reel)
    return ContentSignal(
        platform=Platform.INSTAGRAM,
        external_id=reel["code"],
        url=HttpUrl(INSTAGRAM_REEL_URL.format(reel["code"])),
        title=headline(caption),
        description=clean_html(caption),
        # Cuenta pública que publica (como un canal de YouTube), no un usuario.
        author_name=f"@{source.external_id}",
        published_at=datetime.fromtimestamp(reel["taken_at"], UTC),
        observed_at=observed_at,
        format=ContentFormat.SHORT_VIDEO,
        language=source.language,
        metrics=Metrics(
            views=reel["play_count"],
            likes=reel.get("like_count"),
            comments=reel.get("comment_count"),
        ),
    )
