"""Recolecta señales de todas las fuentes activas y guarda contenidos + snapshots.

    uv run python -m app.jobs.collect                       # backfill de 14 días (primera carga)
    uv run python -m app.jobs.collect --days 7              # ciclo periódico: refresca métricas
    uv run python -m app.jobs.collect --platform hackernews --platform rss

Cada ejecución es un snapshot: las piezas que siguen dentro de la ventana vuelven a leerse con
sus métricas actuales. Así se construye el historial de velocidad.

Un error en una fuente no detiene el resto: queda registrado en `pipeline_runs.stats`.
El consumo de cada API (cuota de YouTube, requests) se guarda en `usage_events` (CLAUDE.md §4).
"""

import argparse
import asyncio
import sys
import time
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from sqlalchemy import select, text

from app.collectors.base import SignalCollector
from app.collectors.hackernews import HackerNewsCollector
from app.collectors.rss import RSSCollector
from app.collectors.scrapecreators import (
    InstagramCollector,
    RedditCollector,
    ScrapeCreatorsClient,
    TikTokCollector,
)
from app.collectors.usage import UsageMeter
from app.collectors.youtube import YouTubeClient, YouTubeCollector
from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.models import PipelineRun, Source
from app.schemas.signal import Platform
from app.services.costs import record_meter
from app.services.signals import store_signals

log = structlog.get_logger()

JOB_NAME = "collect"
LOCK_KEY = 0x0C011EC7  # clave de pg_advisory_lock para este job
CONCURRENCY = 8


def build_collectors(http: httpx.AsyncClient, usage: UsageMeter) -> dict[str, SignalCollector]:
    collectors: dict[str, SignalCollector] = {
        Platform.HACKERNEWS.value: HackerNewsCollector(http, usage),
        Platform.RSS.value: RSSCollector(http, usage),
    }
    settings = get_settings()
    if settings.youtube_api_key:
        collectors[Platform.YOUTUBE.value] = YouTubeCollector(
            YouTubeClient(settings.youtube_api_key, http, usage)
        )
    if settings.scrapecreators_api_key:
        scrapecreators = ScrapeCreatorsClient(settings.scrapecreators_api_key, http, usage)
        collectors[Platform.TIKTOK.value] = TikTokCollector(scrapecreators)
        collectors[Platform.REDDIT.value] = RedditCollector(scrapecreators)
        collectors[Platform.INSTAGRAM.value] = InstagramCollector(scrapecreators)
    return collectors


async def collect_source(
    source: Source, collector: SignalCollector, days: int, sem: asyncio.Semaphore
) -> dict[str, Any]:
    async with sem:
        started = time.monotonic()
        try:
            signals = await collector.collect(source, backfill_days=days)
            async with SessionLocal() as session:
                result = await store_signals(session, source, signals)
            stat = {"items": result.items_upserted, "snapshots": result.snapshots_inserted}
        except Exception as e:  # una fuente rota no tumba el job
            stat = {"error": f"{type(e).__name__}: {e}"[:300]}
        stat["seconds"] = round(time.monotonic() - started, 1)
        log.info("source_collected", source=source.name, platform=source.platform, **stat)
        return stat


async def run(days: int, platforms: list[str] | None, run_id: int | None = None) -> dict[str, Any]:
    async with SessionLocal() as session:
        stmt = select(Source).where(Source.active.is_(True)).order_by(Source.id)
        if platforms:
            stmt = stmt.where(Source.platform.in_(platforms))
        sources = list((await session.scalars(stmt)).all())

    usage = UsageMeter()
    async with httpx.AsyncClient(timeout=30) as http:
        collectors = build_collectors(http, usage)
        runnable = [s for s in sources if s.platform in collectors]
        skipped = sorted({s.platform for s in sources} - collectors.keys())
        if skipped:
            log.warning("platforms_skipped", platforms=skipped, reason="sin collector o sin key")

        sem = asyncio.Semaphore(CONCURRENCY)
        stats = await asyncio.gather(
            *(collect_source(s, collectors[s.platform], days, sem) for s in runnable)
        )

    async with SessionLocal() as session:
        await record_meter(session, usage, pipeline_run_id=run_id)

    per_source = {f"{s.platform}:{s.name}": st for s, st in zip(runnable, stats, strict=True)}
    return {
        "days": days,
        "sources": len(runnable),
        "failed": sum(1 for st in stats if "error" in st),
        "items": sum(st.get("items", 0) for st in stats),
        "snapshots": sum(st.get("snapshots", 0) for st in stats),
        "skipped_platforms": skipped,
        "per_source": per_source,
    }


async def main(days: int, platforms: list[str] | None) -> int:
    # Lock a nivel de conexión: impide dos ejecuciones simultáneas del job (CLAUDE.md §4).
    async with engine.connect() as lock_conn:
        got_lock = await lock_conn.scalar(text("select pg_try_advisory_lock(:k)"), {"k": LOCK_KEY})
        if not got_lock:
            print("⚠ Ya hay un collect en curso; se omite esta ejecución.")
            return 0

        async with SessionLocal() as session:
            run_row = PipelineRun(job=JOB_NAME, status="running")
            session.add(run_row)
            await session.commit()

            try:
                summary = await run(days, platforms, run_row.id)
                run_row.status = "success" if summary["failed"] < summary["sources"] else "failed"
                run_row.stats = summary
            except Exception as e:
                run_row.status, run_row.error = "failed", f"{type(e).__name__}: {e}"
                raise
            finally:
                run_row.finished_at = datetime.now(UTC)
                await session.commit()
                await lock_conn.execute(text("select pg_advisory_unlock(:k)"), {"k": LOCK_KEY})

    print(
        f"✓ run #{run_row.id}: {summary['sources']} fuentes · {summary['items']} piezas · "
        f"{summary['snapshots']} snapshots · {summary['failed']} con error"
    )
    for name, st in summary["per_source"].items():
        if "error" in st:
            print(f"  ✗ {name}: {st['error']}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=14, help="ventana de backfill/refresco")
    parser.add_argument("--platform", action="append", choices=[p.value for p in Platform])
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.days, args.platform)))
