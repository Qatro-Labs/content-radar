import httpx
import respx
from sqlalchemy import select

from app.collectors.youtube import API_BASE, YouTubeClient
from app.jobs.seed_sources import DEFAULT_FILE, SeedFile, load_seed_file, seed
from app.models import Source

SEED = SeedFile.model_validate(
    {
        "youtube": [
            {"handle": "@DotCSV", "segment": "latam_es", "language": "es", "region": "es"},
            {"handle": "@noexiste", "segment": "tech"},
        ],
        "hackernews": [{"query": "AI agents", "segment": "tech"}],
        "rss": [
            {
                "name": "Xataka IA",
                "url": "https://www.xataka.com/tag/inteligencia-artificial/rss2.xml",
                "segment": "latam_es",
                "language": "es",
                "ai_filter": True,
            }
        ],
    }
)


def channels_response(request: httpx.Request) -> httpx.Response:
    if request.url.params["forHandle"] == "@DotCSV":
        item = {
            "id": "UCy5znSnfMsDwaLlROnZ7Qbg",
            "snippet": {"title": "Dot CSV"},
            "contentDetails": {"relatedPlaylists": {"uploads": "UUy5znSnfMsDwaLlROnZ7Qbg"}},
        }
        return httpx.Response(200, json={"items": [item]})
    return httpx.Response(200, json={"items": []})


def test_repo_seed_file_is_valid():
    data = load_seed_file(DEFAULT_FILE)
    assert data.youtube and data.hackernews and data.rss
    handles = [s.handle for s in data.youtube]
    assert len(handles) == len(set(handles))


@respx.mock
async def test_seed_resolves_handles_and_is_idempotent(session):
    respx.get(f"{API_BASE}/channels").mock(side_effect=channels_response)
    async with httpx.AsyncClient() as http:
        yt = YouTubeClient("test-key", http)
        report = await seed(session, SEED, yt)
        await seed(session, SEED, yt)  # segunda vez: actualiza, no duplica

    assert report["youtube"] == 1
    assert report["youtube_unresolved"] == ["@noexiste"]

    sources = (await session.scalars(select(Source).order_by(Source.platform))).all()
    assert [s.platform for s in sources] == ["hackernews", "rss", "youtube"]

    yt_src = sources[2]
    assert yt_src.external_id == "UCy5znSnfMsDwaLlROnZ7Qbg"
    assert yt_src.segment == "latam_es"
    assert yt_src.config["uploads_playlist_id"] == "UUy5znSnfMsDwaLlROnZ7Qbg"
    assert sources[1].config == {"ai_filter": True}


async def test_seed_without_youtube_key_skips_channels(session):
    report = await seed(session, SEED, youtube=None)
    assert report["youtube_skipped"] == 2
    assert report["rss"] == 1 and report["hackernews"] == 1
