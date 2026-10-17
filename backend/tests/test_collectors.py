from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest
import respx

from app.collectors.hackernews import API_URL as HN_URL
from app.collectors.hackernews import HackerNewsCollector
from app.collectors.rss import RSSCollector
from app.collectors.text import clean_html, is_ai_related
from app.collectors.youtube import API_BASE, YouTubeClient, YouTubeCollector, parse_duration
from app.models import Source
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
