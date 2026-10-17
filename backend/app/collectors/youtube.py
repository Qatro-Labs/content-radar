"""Cliente de YouTube Data API v3.

Por ahora solo resuelve handles → canal. El collector de vídeos (playlistItems + videos.list)
se añade en el paso 4.

Coste de cuota: channels.list = 1 unidad por llamada (cuota diaria por defecto: 10.000).
"""

from dataclasses import dataclass

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

API_BASE = "https://www.googleapis.com/youtube/v3"


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
    def __init__(self, api_key: str, client: httpx.AsyncClient):
        if not api_key:
            raise YouTubeError("YOUTUBE_API_KEY no está configurada")
        self._key = api_key
        self._http = client

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
    )
    async def _get(self, resource: str, **params: str) -> dict:
        r = await self._http.get(f"{API_BASE}/{resource}", params={**params, "key": self._key})
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
