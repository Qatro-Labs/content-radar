"""X (Twitter) vía twitterapi.io (proveedor de datos públicos, pago por tweet devuelto).

Últimos tweets de perfiles elegidos a mano, como un canal de YouTube: el outlier se mide contra la
mediana del mismo perfil. ScrapeCreators no sirve para esto: su endpoint de perfil devuelve los 100
tweets más populares de toda la historia de la cuenta, ninguno reciente (probado el 18/10).

Coste: 0,15 $ por 1.000 tweets devueltos, con un mínimo de un tweet por llamada. Una llamada por
perfil y ejecución: la primera página, con hasta 20 tweets.
"""

import asyncio
import html
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx
from pydantic import HttpUrl
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.collectors.text import clean_html, headline, is_ai_related
from app.collectors.usage import UsageMeter
from app.models import Source
from app.schemas.cost import Provider
from app.schemas.signal import ContentFormat, ContentSignal, Metrics, Platform

API_BASE = "https://api.twitterapi.io"
LAST_TWEETS_PATH = "/twitter/user/last_tweets"
TWEET_URL = "https://x.com/{}/status/{}"
TWEET_DATE_FORMAT = "%a %b %d %H:%M:%S %z %Y"
# Enlaces que apuntan al propio X (otro tweet, una imagen): no unen fuentes.
X_HOSTS = ("x.com", "twitter.com", "t.co")
# La cuenta gratuita admite una llamada cada 5 s; si no, responde 429. Con ~15 perfiles son ~80 s.
MIN_CALL_INTERVAL_SECONDS = 5.5
SUCCESS = "success"


class TwitterApiError(Exception):
    """twitterapi.io respondió 200 con `status: error` (p. ej. un perfil que no existe)."""


class TwitterApiClient:
    def __init__(self, api_key: str, client: httpx.AsyncClient, usage: UsageMeter):
        self._key = api_key
        self._http = client
        self.usage = usage
        # Las fuentes se recolectan en paralelo: el lock las pone en fila para respetar el límite.
        self._lock = asyncio.Lock()
        self._next_call_at = 0.0

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
    )
    async def last_tweets(self, handle: str) -> list[dict]:
        async with self._lock:
            await asyncio.sleep(max(self._next_call_at - time.monotonic(), 0))
            try:
                r = await self._http.get(
                    f"{API_BASE}{LAST_TWEETS_PATH}",
                    params={"userName": handle},
                    headers={"X-API-Key": self._key},
                )
            finally:
                self._next_call_at = time.monotonic() + MIN_CALL_INTERVAL_SECONDS
        r.raise_for_status()
        body = r.json()
        if body.get("status") != SUCCESS:
            raise TwitterApiError(body.get("msg") or body.get("message") or "sin detalle")
        tweets = (body.get("data") or {}).get("tweets") or []
        self.usage.add(Provider.TWITTERAPI, LAST_TWEETS_PATH, units=max(len(tweets), 1))
        return tweets


class XCollector:
    """`source.external_id` = handle del perfil (sin `@`)."""

    def __init__(self, client: TwitterApiClient):
        self._api = client

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]:
        tweets = await self._api.last_tweets(source.external_id)
        observed_at = datetime.now(UTC)
        since = observed_at - timedelta(days=backfill_days)
        ai_filter = source.config.get("ai_filter", False)
        return [
            _tweet_signal(tweet, source, observed_at)
            for tweet in tweets
            if _keep_tweet(tweet, since, ai_filter=ai_filter)
        ]


def _published_at(tweet: dict) -> datetime:
    return datetime.strptime(tweet["createdAt"], TWEET_DATE_FORMAT)


def _keep_tweet(tweet: dict, since: datetime, *, ai_filter: bool) -> bool:
    text = clean_html(tweet.get("text"))
    return bool(
        tweet.get("id")
        and text
        # Un retweet es contenido de otra cuenta, con otra audiencia: compararlo con la mediana del
        # perfil daría outliers falsos. Las respuestas son conversación, no publicación.
        and not tweet.get("retweeted_tweet")
        and not tweet.get("isReply")
        and tweet.get("viewCount") is not None
        and _published_at(tweet) >= since
        and (not ai_filter or is_ai_related(text))
    )


def _target_url(tweet: dict) -> HttpUrl | None:
    for link in (tweet.get("entities") or {}).get("urls") or []:
        url = link.get("expanded_url") or ""
        host = urlparse(url).hostname or ""
        if host and host.removeprefix("www.") not in X_HOSTS:
            return HttpUrl(url)
    return None


def _tweet_signal(tweet: dict, source: Source, observed_at: datetime) -> ContentSignal:
    text = clean_html(tweet["text"]) or ""
    return ContentSignal(
        platform=Platform.X,
        external_id=tweet["id"],
        url=HttpUrl(TWEET_URL.format(source.external_id, tweet["id"])),
        target_url=_target_url(tweet),
        title=headline(html.unescape(tweet["text"])),
        description=text,
        # Cuenta pública que publica (como un canal de YouTube), no un usuario.
        author_name=f"@{source.external_id}",
        published_at=_published_at(tweet),
        observed_at=observed_at,
        format=ContentFormat.POST,
        language=source.language,
        metrics=Metrics(
            views=tweet["viewCount"],
            likes=tweet.get("likeCount"),
            comments=tweet.get("replyCount"),
            shares=tweet.get("retweetCount"),
        ),
    )
