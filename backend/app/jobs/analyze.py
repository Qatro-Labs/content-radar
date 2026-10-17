"""Calcula las oportunidades a partir de las piezas recolectadas y las guarda por ejecución.

    uv run python -m app.jobs.analyze

clasificar cada pieza con Jev (cacheado) → embed → cluster → scores deterministas → persistir.
Sin LLM por ahora: los campos del LLM quedan en null (CLAUDE.md §2, regla 3). Sin
TYPESAFE_API_KEY, o si Jev falla, las piezas quedan sin clasificar y el job sigue.
"""

import asyncio
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.usage import UsageMeter
from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.intelligence.jev import build_judge, to_piece_judgment
from app.intelligence.opportunities import TopicResult
from app.models import PipelineRun
from app.services.classification import ClassificationStats, classify_pieces, load_judgments
from app.services.costs import record_meter
from app.services.opportunities import (
    ANALYZE_JOB,
    compute_opportunities,
    load_pieces,
    save_opportunities,
)

log = structlog.get_logger()

LOCK_KEY = 0x0A7A1F2E  # clave de pg_advisory_lock para este job


async def _run(
    session: AsyncSession, run_row: PipelineRun
) -> tuple[ClassificationStats, list[TopicResult], dict[str, Any]]:
    as_of = datetime.now(UTC)
    loaded = await load_pieces(session, as_of)
    meter = UsageMeter()
    jev = await classify_pieces(session, loaded, judge=build_judge(get_settings()), meter=meter)
    await record_meter(session, meter, pipeline_run_id=run_row.id)
    answers = await load_judgments(session, loaded)
    judgments = {item_id: to_piece_judgment(item_id, a) for item_id, a in answers.items()}
    computed = await compute_opportunities(session, as_of, pieces=loaded, judgments=judgments)
    results = computed.results
    await save_opportunities(session, run_row.id, results)
    lifecycles: dict[str, int] = {}
    for r in results:
        key = r.opportunity.lifecycle.value
        lifecycles[key] = lifecycles.get(key, 0) + 1
    stats: dict[str, Any] = {
        "as_of": as_of.isoformat(),
        "pieces": computed.analyzed,
        "off_topic_removed": computed.off_topic_removed,
        "opportunities": len(results),
        "lifecycle": lifecycles,
        "jev": asdict(jev),
    }
    run_row.status, run_row.stats = "success", stats
    return jev, results, stats


def _print_summary(
    run_id: int,
    stats: dict[str, Any],
    *,
    jev: ClassificationStats,
    results: list[TopicResult],
) -> None:
    print(
        f"✓ run #{run_id}: {stats['pieces']} piezas · {len(results)} oportunidades · "
        f"{stats['lifecycle']}"
    )
    print(f"  filtro about_ai: {stats['off_topic_removed']} piezas fuera de tema quitadas")
    print(f"  jev: {jev.classified} clasificadas · {jev.cached} de caché · {jev.failed} fallidas")
    if jev.skipped_reason:
        print(f"  jev omitido: {jev.skipped_reason}")
    for r in results[:10]:
        o = r.opportunity
        print(
            f"  {o.momentum_score:5.1f}  {o.lifecycle.value:12} acc {o.acceleration:+.2f}  "
            f"{o.source_count} fuentes  {o.outlier_count} outliers  {o.topic[:70]}"
        )


async def main() -> int:
    async with engine.connect() as lock_conn:
        got_lock = await lock_conn.scalar(text("select pg_try_advisory_lock(:k)"), {"k": LOCK_KEY})
        if not got_lock:
            print("⚠ Ya hay un analyze en curso; se omite esta ejecución.")
            return 0

        async with SessionLocal() as session:
            run_row = PipelineRun(job=ANALYZE_JOB, status="running")
            session.add(run_row)
            await session.commit()

            try:
                jev, results, stats = await _run(session, run_row)
            except Exception as e:
                await session.rollback()
                run_row.status, run_row.error = "failed", f"{type(e).__name__}: {e}"
                raise
            finally:
                run_row.finished_at = datetime.now(UTC)
                session.add(run_row)
                await session.commit()
                await lock_conn.execute(text("select pg_advisory_unlock(:k)"), {"k": LOCK_KEY})

    log.info("analyze_done", run=run_row.id, stats=run_row.stats)
    _print_summary(run_row.id, stats, jev=jev, results=results)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
