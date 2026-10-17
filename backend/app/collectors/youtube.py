"""YouTube Data API v3: resolución de handles y collector de vídeos.

Coste de cuota (cuota diaria por defecto: 10.000 unidades):
- channels.list, playlistItems.list, videos.list = 1 unidad por llamada.
- search.list = 100 unidades → no se usa; leemos el playlist de subidas de cada canal.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.collectors.text import clean_html, is_ai_related
from app.collectors.usage import UsageMeter
from app.models import Source
from app.schemas.cost import Provider
from app.schemas.signal import ContentFormat, ContentSignal, Metrics, Platform

API_BASE = "https://www.googleapis.com/youtube/v3"
SHORT_MAX_SECONDS = 180  # los Shorts pueden durar hasta 3 min
MAX_UPLOAD_PAGES = 4  # 200 vídeos por canal como máximo en un backfill
FILTER_DESCRIPTION_CHARS = 200
# Unidades de cuota por llamada, según la tabla oficial (cuenta también si la llamada falla):
# https://developers.google.com/youtube/v3/determine_quota_cost
QUOTA_COST = {"channels": 1, "playlistItems": 1, "videos": 1, "search": 100}


class YouTubeError(Exception):
    pass


@dataclass(frozen=True)
class Channel:
    id: str
    title: str
    uploads_playlist_id: str

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/channel/{self.id}"


class YouTubeClient:
    def __init__(self, api_key: str, client: httpx.AsyncClient, usage: UsageMeter | None = None):
        if not api_key:
            raise YouTubeError("YOUTUBE_API_KEY no está configurada")
        self._key = api_key
        self._http = client
        self.usage = usage or UsageMeter()

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
    )
    async def _get(self, resource: str, **params: str) -> dict:
        r = await self._http.get(f"{API_BASE}/{resource}", params={**params, "key": self._key})
        self.usage.add(Provider.YOUTUBE, f"{resource}.list", QUOTA_COST[resource])
        if r.status_code != 200:
            # El mensaje de la API explica el motivo (cuota, key inválida…); nunca incluye la key.
            reason = r.json().get("error", {}).get("message", r.text[:200])
            raise YouTubeError(f"{resource} → HTTP {r.status_code}: {reason}")
        return r.json()

    async def channel_by_handle(self, handle: str) -> Channel | None:
        data = await self._get("channels", part="snippet,contentDetails", forHandle=handle)
        items = data.get("items") or []
        if not items:
            return None
        ch = items[0]
        return Channel(
            id=ch["id"],
            title=ch["snippet"]["title"],
            uploads_playlist_id=ch["contentDetails"]["relatedPlaylists"]["uploads"],
        )

    async def recent_upload_ids(self, playlist_id: str, since: datetime) -> list[str]:
        """IDs de vídeos subidos desde `since` (el playlist viene ordenado del más nuevo)."""
        ids: list[str] = []
        page_token = ""
        for _ in range(MAX_UPLOAD_PAGES):
            params = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": "50"}
            if page_token:
                params["pageToken"] = page_token
            data = await self._get("playlistItems", **params)
            for item in data.get("items", []):
                details = item["contentDetails"]
                published = details.get("videoPublishedAt")
                if published and _parse_dt(published) < since:
                    return ids
                ids.append(details["videoId"])
            page_token = data.get("nextPageToken", "")
            if not page_token:
                break
        return ids

    async def videos(self, video_ids: list[str]) -> list[dict]:
        out: list[dict] = []
        for batch in _chunks(video_ids, 50):
            data = await self._get(
                "videos", part="snippet,statistics,contentDetails", id=",".join(batch)
            )
            out.extend(data.get("items", []))
        return out


_DURATION = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def parse_duration(value: str | None) -> int | None:
    """ISO 8601 (PT1H2M3S) → segundos."""
    m = _DURATION.fullmatch(value or "")
    if not m or not any(m.groups()):
        return None
    d, h, mi, s = (int(g or 0) for g in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _chunks(items: list[str], size: int) -> Iterator[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _int(value: str | None) -> int | None:
    return int(value) if value is not None else None


class YouTubeCollector:
    def __init__(self, client: YouTubeClient):
        self._yt = client

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]:
        observed_at = datetime.now(UTC)
        playlist_id = source.config.get("uploads_playlist_id")
        if not playlist_id:
            raise YouTubeError(f"La fuente {source.name} no tiene uploads_playlist_id")
        ai_filter = source.config.get("ai_filter", False)

        ids = await self._yt.recent_upload_ids(
            playlist_id, observed_at - timedelta(days=backfill_days)
        )
        signals: list[ContentSignal] = []
        for video in await self._yt.videos(ids):
            snippet, stats = video["snippet"], video.get("statistics", {})
            if snippet.get("liveBroadcastContent") in ("live", "upcoming"):
                continue
            title, description = snippet["title"], snippet.get("description")
            # Solo el inicio de la descripción: el resto suele ser patrocinios y enlaces que
            # mencionan IA aunque el vídeo no trate de IA.
            intro = (description or "")[:FILTER_DESCRIPTION_CHARS]
            tags = " ".join(snippet.get("tags", []))
            if ai_filter and not is_ai_related(title, intro, tags):
                continue
            duration = parse_duration(video.get("contentDetails", {}).get("duration"))
            language = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage")
            signals.append(
                ContentSignal(
                    platform=Platform.YOUTUBE,
                    external_id=video["id"],
                    url=f"https://www.youtube.com/watch?v={video['id']}",
                    title=title,
                    description=clean_html(description),
                    author_name=snippet.get("channelTitle"),
                    published_at=_parse_dt(snippet["publishedAt"]),
                    observed_at=observed_at,
                    format=(
                        ContentFormat.SHORT_VIDEO
                        if duration is not None and duration <= SHORT_MAX_SECONDS
                        else ContentFormat.LONG_VIDEO
                    ),
                    language=(language or source.language or "")[:2] or None,
                    duration_seconds=duration,
                    # Las métricas ocultas por el canal llegan ausentes → None, no 0.
                    metrics=Metrics(
                        views=_int(stats.get("viewCount")),
                        likes=_int(stats.get("likeCount")),
                        comments=_int(stats.get("commentCount")),
                    ),
                )
            )
        return signals
