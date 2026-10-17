from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest
import respx

from app.collectors.hackernews import API_URL as HN_URL
from app.collectors.hackernews import HackerNewsCollector
from app.collectors.rss import RSSCollector
from app.collectors.scrapecreators import API_BASE as SC_API
from app.collectors.scrapecreators import RedditCollector, ScrapeCreatorsClient, TikTokCollector
from app.collectors.text import clean_html, is_ai_related
from app.collectors.usage import UsageMeter
from app.collectors.youtube import API_BASE, YouTubeClient, YouTubeCollector, parse_duration
from app.models import Source
from app.schemas.cost import Provider
from app.schemas.signal import ContentFormat

NOW = datetime.now(UTC)


def make_source(platform: str, external_id: str, **config) -> Source:
    return Source(
        id=1,
        platform=platform,
        kind="feed",
        external_id=external_id,
        name="Fuente Test",
        segment="latam_es",
        language="es",
        config=config,
    )


# --- filtro de IA -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Cómo la IA cambia las ventas", True),
        ("Nuevo modelo de OpenAI", True),
        ("Agentes de IA para equipos comerciales", True),
        ("Claude Code ya soporta MCP", True),
        ("Las mejores ofertas del día en tecnología", False),  # "ía" no es "IA"
        ("Said the CEO in Paris", False),  # "ai" dentro de palabras no cuenta
    ],
)
def test_is_ai_related(text, expected):
    assert is_ai_related(text) is expected


def test_clean_html():
    assert clean_html("<p>Hola&nbsp;<b>mundo</b></p>\n\n") == "Hola mundo"
    assert clean_html(None) is None


# --- Hacker News --------------------------------------------------------------------------


@respx.mock
async def test_hackernews_maps_hits_without_personal_data():
    created = int((NOW - timedelta(days=1)).timestamp())
    route = respx.get(HN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "nbPages": 1,
                "hits": [
                    {
                        "objectID": "4242",
                        "title": "Show HN: AI agents for sales teams",
                        "url": "https://example.com/agents",
                        "author": "someuser",
                        "points": 120,
                        "num_comments": 45,
                        "created_at_i": created,
                    },
                    {"objectID": "9", "title": None, "created_at_i": created},  # sin título
                ],
            },
        )
    )
    async with httpx.AsyncClient() as http:
        signals = await HackerNewsCollector(http).collect(
            make_source("hackernews", "AI agents"), backfill_days=7
        )

    assert route.calls[0].request.url.params["query"] == "AI agents"
    assert len(signals) == 1
    s = signals[0]
    assert str(s.url) == "https://news.ycombinator.com/item?id=4242"
    assert str(s.target_url) == "https://example.com/agents"
    assert s.author_name is None
    assert (s.metrics.points, s.metrics.comments) == (120, 45)
    assert s.format is ContentFormat.DISCUSSION


# --- RSS ----------------------------------------------------------------------------------


def rss_feed(*items: tuple[str, datetime]) -> str:
    entries = "".join(
        f"<item><title>{t}</title><link>https://medio.test/{i}</link><guid>g{i}</guid>"
        f"<pubDate>{format_datetime(d)}</pubDate><description>&lt;p&gt;{t}&lt;/p&gt;</description></item>"
        for i, (t, d) in enumerate(items)
    )
    channel = f"<channel><title>T</title>{entries}</channel>"
    return f'<?xml version="1.0"?><rss version="2.0">{channel}</rss>'


@respx.mock
async def test_rss_applies_window_and_ai_filter():
    url = "https://medio.test/feed"
    respx.get(url).mock(
        return_value=httpx.Response(
            200,
            text=rss_feed(
                ("La IA llega a las pymes", NOW - timedelta(days=1)),
                ("Ofertas del día en televisores", NOW - timedelta(days=1)),  # filtrado: no es IA
                ("OpenAI anuncia un modelo", NOW - timedelta(days=30)),  # fuera de ventana
            ),
        )
    )
    async with httpx.AsyncClient() as http:
        signals = await RSSCollector(http).collect(
            make_source("rss", url, ai_filter=True), backfill_days=14
        )

    assert [s.title for s in signals] == ["La IA llega a las pymes"]
    s = signals[0]
    assert s.external_id == "g0"
    assert s.description == "La IA llega a las pymes"
    assert s.author_name == "Fuente Test"
    assert s.language == "es"


# --- YouTube ------------------------------------------------------------------------------


def test_parse_duration():
    assert parse_duration("PT1H2M3S") == 3723
    assert parse_duration("PT45S") == 45
    assert parse_duration("P0D") == 0
    assert parse_duration(None) is None


@respx.mock
async def test_youtube_collects_recent_uploads_with_metrics():
    recent = (NOW - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    old = (NOW - timedelta(days=40)).isoformat().replace("+00:00", "Z")
    respx.get(f"{API_BASE}/playlistItems").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {"contentDetails": {"videoId": "short1", "videoPublishedAt": recent}},
                    {"contentDetails": {"videoId": "long1", "videoPublishedAt": recent}},
                    {"contentDetails": {"videoId": "old1", "videoPublishedAt": old}},
                ],
                "nextPageToken": "never-requested",
            },
        )
    )
    videos = respx.get(f"{API_BASE}/videos").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "short1",
                        "snippet": {
                            "title": "IA en 60 segundos",
                            "publishedAt": recent,
                            "channelTitle": "Canal",
                            "defaultAudioLanguage": "es-419",
                        },
                        "statistics": {"viewCount": "5000", "likeCount": "300"},  # sin comentarios
                        "contentDetails": {"duration": "PT58S"},
                    },
                    {
                        "id": "long1",
                        "snippet": {
                            "title": "Agentes de IA: guía completa",
                            "publishedAt": recent,
                            "channelTitle": "Canal",
                        },
                        "statistics": {
                            "viewCount": "12000",
                            "likeCount": "800",
                            "commentCount": "90",
                        },
                        "contentDetails": {"duration": "PT25M10S"},
                    },
                ]
            },
        )
    )
    source = make_source("youtube", "UC1", uploads_playlist_id="UU1")
    async with httpx.AsyncClient() as http:
        signals = await YouTubeCollector(YouTubeClient("k", http)).collect(source, backfill_days=14)

    assert videos.calls[0].request.url.params["id"] == "short1,long1"  # el vídeo viejo no se pide
    by_id = {s.external_id: s for s in signals}
    assert by_id["short1"].format is ContentFormat.SHORT_VIDEO
    assert by_id["short1"].language == "es"
    assert by_id["short1"].metrics.comments is None  # oculto ≠ 0
    assert by_id["long1"].format is ContentFormat.LONG_VIDEO
    assert by_id["long1"].metrics.views == 12000


# --- ScrapeCreators: TikTok y Reddit ------------------------------------------------------


def tiktok_video(video_id: str, desc: str, *, plays: int = 5000, region: str = "MX", **extra):
    return {
        "aweme_id": video_id,
        "desc": desc,
        "desc_language": "es",
        "region": region,
        "create_time": int((NOW - timedelta(days=1)).timestamp()),
        "author": {"unique_id": "creadora", "nickname": "Creadora"},
        "statistics": {
            "play_count": plays,
            "digg_count": 300,
            "comment_count": 12,
            "share_count": 40,
        },
        "video": {"duration": 45300},
        **extra,
    }


@respx.mock
async def test_tiktok_maps_videos_and_filters_noise():
    route = respx.get(f"{SC_API}/v1/tiktok/search/keyword").mock(
        return_value=httpx.Response(
            200,
            json={
                "search_item_list": [
                    tiktok_video("1", "Agentes de IA en la empresa\n#ia #negocios"),
                    tiktok_video("1", "Agentes de IA en la empresa"),  # repetido
                    tiktok_video("2", "La IA en pymes", region="ES"),  # fuera de LATAM
                    tiktok_video("3", "Promo de IA", plays=3),  # sin tracción
                    tiktok_video("4", "Disturbios en el centro"),  # no es IA
                    tiktok_video("5", "IA para ventas", is_ad=True),  # anuncio
                ]
            },
        )
    )
    source = make_source(
        "tiktok",
        "agentes de IA|CO",
        query="agentes de IA",
        search_region="CO",
        item_regions=["MX", "CO"],
        ai_filter=True,
    )
    usage = UsageMeter()
    async with httpx.AsyncClient() as http:
        collector = TikTokCollector(ScrapeCreatorsClient("k", http, usage))
        signals = await collector.collect(source)

    params = route.calls[0].request.url.params
    assert (params["query"], params["region"]) == ("agentes de IA", "CO")
    assert route.calls[0].request.headers["x-api-key"] == "k"
    assert usage.counts[(Provider.SCRAPECREATORS, "/v1/tiktok/search/keyword")].calls == 1
    assert [s.external_id for s in signals] == ["1"]
    s = signals[0]
    assert str(s.url) == "https://www.tiktok.com/@creadora/video/1"
    assert s.title == "Agentes de IA en la empresa"
    assert s.author_name == "@creadora"
    assert s.format is ContentFormat.SHORT_VIDEO
    assert s.duration_seconds == 45
    assert (s.metrics.views, s.metrics.likes, s.metrics.comments, s.metrics.shares) == (
        5000,
        300,
        12,
        40,
    )


@respx.mock
async def test_reddit_maps_posts_without_personal_data():
    created = int((NOW - timedelta(hours=10)).timestamp())
    respx.get(f"{SC_API}/v1/reddit/subreddit").mock(
        return_value=httpx.Response(
            200,
            json={
                "posts": [
                    {
                        "id": "abc",
                        "title": "Claude ships computer use for teams",
                        "selftext": "",
                        "author": "someone",
                        "subreddit": "OpenAI",
                        "score": 812,
                        "num_comments": 140,
                        "created_utc": created,
                        "url": "https://www.anthropic.com/news/teams",
                    },
                    {
                        "id": "img",
                        "title": "Meme sobre GPT",
                        "subreddit": "OpenAI",
                        "score": 300,
                        "num_comments": 5,
                        "created_utc": created,
                        "url": "https://i.redd.it/x.jpeg",
                    },
                    {
                        "id": "low",
                        "title": "Pregunta sobre LLMs",
                        "subreddit": "OpenAI",
                        "score": 2,
                        "created_utc": created,
                    },
                ]
            },
        )
    )
    async with httpx.AsyncClient() as http:
        collector = RedditCollector(ScrapeCreatorsClient("k", http, UsageMeter()))
        signals = await collector.collect(make_source("reddit", "OpenAI"))

    assert [s.external_id for s in signals] == ["abc", "img"]
    post, image = signals
    assert str(post.url) == "https://www.reddit.com/r/OpenAI/comments/abc/"
    assert str(post.target_url) == "https://www.anthropic.com/news/teams"
    assert image.target_url is None  # contenido alojado en Reddit: no une fuentes
    assert post.author_name is None
    assert post.description is None
    assert (post.metrics.points, post.metrics.comments) == (812, 140)


@respx.mock
async def test_scrapecreators_does_not_retry_paid_errors():
    route = respx.get(f"{SC_API}/v1/reddit/subreddit").mock(return_value=httpx.Response(402))
    usage = UsageMeter()
    async with httpx.AsyncClient() as http:
        collector = RedditCollector(ScrapeCreatorsClient("k", http, usage))
        with pytest.raises(httpx.HTTPStatusError):
            await collector.collect(make_source("reddit", "OpenAI"))

    assert route.call_count == 1
    assert not usage.counts  # un error no gasta crédito: no cuenta como coste medido
