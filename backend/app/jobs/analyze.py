"""Calcula las oportunidades a partir de las piezas recolectadas y las guarda por ejecución.

    uv run python -m app.jobs.analyze

embed → cluster → scores deterministas → persistir. Sin LLM por ahora: los campos del LLM
quedan en null (CLAUDE.md §2, regla 3).
"""

import asyncio
import sys
from datetime import UTC, datetime

import structlog
from sqlalchemy import text

from app.db.session import SessionLocal, engine
from app.models import PipelineRun
from app.services.opportunities import ANALYZE_JOB, compute_opportunities, save_opportunities

log = structlog.get_logger()

LOCK_KEY = 0x0A7A1F2E  # clave de pg_advisory_lock para este job


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
                as_of = datetime.now(UTC)
                pieces, results = await compute_opportunities(session, run_row.id, as_of)
                await save_opportunities(session, run_row.id, results)
                lifecycles: dict[str, int] = {}
                for r in results:
                    key = r.opportunity.lifecycle.value
                    lifecycles[key] = lifecycles.get(key, 0) + 1
                run_row.status = "success"
                run_row.stats = {
                    "as_of": as_of.isoformat(),
                    "pieces": pieces,
                    "opportunities": len(results),
                    "lifecycle": lifecycles,
                }
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
    print(f"✓ run #{run_row.id}: {pieces} piezas · {len(results)} oportunidades · {lifecycles}")
    for r in results[:10]:
        o = r.opportunity
        print(
            f"  {o.momentum_score:5.1f}  {o.lifecycle.value:12} acc {o.acceleration:+.2f}  "
            f"{o.source_count} fuentes  {o.outlier_count} outliers  {o.topic[:70]}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
