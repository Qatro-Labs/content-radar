"""Carga data/sources.yaml en la tabla `sources` (idempotente: upsert por platform + external_id).

    uv run python -m app.jobs.seed_sources            # carga todo
    uv run python -m app.jobs.seed_sources --dry-run  # solo valida el YAML

Sin YOUTUBE_API_KEY se cargan HN y RSS y se omiten los canales de YouTube (aviso, no error).
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml
from pydantic import BaseModel, HttpUrl
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.usage import UsageMeter
from app.collectors.youtube import YouTubeClient, YouTubeError
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Source
from app.schemas.signal import Platform, Segment, SourceKind
from app.services.costs import record_meter

DEFAULT_FILE = Path(__file__).resolve().parents[3] / "data" / "sources.yaml"


class _Common(BaseModel):
    segment: Segment
    language: str | None = None
    region: str | None = None
    ai_filter: bool = False
    active: bool = True


class YouTubeSeed(_Common):
    handle: str


class HackerNewsSeed(_Common):
    query: str


class RSSSeed(_Common):
    name: str
    url: HttpUrl


class SeedFile(BaseModel):
    youtube: list[YouTubeSeed] = []
    hackernews: list[HackerNewsSeed] = []
    rss: list[RSSSeed] = []


def load_seed_file(path: Path) -> SeedFile:
    return SeedFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


async def upsert_source(session: AsyncSession, **values: Any) -> None:
    stmt = insert(Source).values(**values)
    updatable = {k: stmt.excluded[k] for k in values if k not in ("platform", "external_id")}
    await session.execute(
        stmt.on_conflict_do_update(index_elements=["platform", "external_id"], set_=updatable)
    )


def _common(seed: _Common) -> dict[str, Any]:
    return {
        "segment": seed.segment.value,
        "language": seed.language,
        "region": seed.region,
        "active": seed.active,
    }


async def seed(session: AsyncSession, data: SeedFile, youtube: YouTubeClient | None) -> dict:
    report: dict[str, Any] = {"hackernews": 0, "rss": 0, "youtube": 0, "youtube_unresolved": []}

    for s in data.hackernews:
        await upsert_source(
            session,
            platform=Platform.HACKERNEWS.value,
            kind=SourceKind.QUERY.value,
            external_id=s.query,
            name=f"HN · {s.query}",
            url=f"https://hn.algolia.com/?q={s.query.replace(' ', '+')}",
            config={"ai_filter": s.ai_filter},
            **_common(s),
        )
        report["hackernews"] += 1

    for s in data.rss:
        await upsert_source(
            session,
            platform=Platform.RSS.value,
            kind=SourceKind.FEED.value,
            external_id=str(s.url),
            name=s.name,
            url=str(s.url),
            config={"ai_filter": s.ai_filter},
            **_common(s),
        )
        report["rss"] += 1

    # HN y RSS quedan guardados aunque YouTube falle después (cuota, key inválida).
    await session.commit()

    if youtube is None:
        report["youtube_skipped"] = len(data.youtube)
    else:
        for s in data.youtube:
            channel = await youtube.channel_by_handle(s.handle)
            if channel is None:
                report["youtube_unresolved"].append(s.handle)
                continue
            await upsert_source(
                session,
                platform=Platform.YOUTUBE.value,
                kind=SourceKind.CHANNEL.value,
                external_id=channel.id,
                name=channel.title,
                url=channel.url,
                config={
                    "handle": s.handle,
                    "uploads_playlist_id": channel.uploads_playlist_id,
                    "ai_filter": s.ai_filter,
                },
                **_common(s),
            )
            report["youtube"] += 1

    await session.commit()
    return report


async def main(path: Path, dry_run: bool) -> int:
    data = load_seed_file(path)
    print(
        f"{path.name}: {len(data.youtube)} YouTube · {len(data.hackernews)} HN · "
        f"{len(data.rss)} RSS"
    )
    if dry_run:
        return 0

    api_key = get_settings().youtube_api_key
    usage = UsageMeter()
    async with httpx.AsyncClient(timeout=20) as http, SessionLocal() as session:
        youtube = YouTubeClient(api_key, http, usage) if api_key else None
        if youtube is None:
            print("⚠ YOUTUBE_API_KEY vacía: se omiten los canales de YouTube.")
        try:
            report = await seed(session, data, youtube)
        except YouTubeError as e:
            print(f"✗ YouTube: {e}", file=sys.stderr)
            return 1
        finally:
            # La cuota se gasta aunque la resolución de handles falle a medias.
            await record_meter(session, usage)

    print(f"✓ cargadas: {report}")
    if report["youtube_unresolved"]:
        print(f"⚠ handles sin canal: {report['youtube_unresolved']}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.file, args.dry_run)))
