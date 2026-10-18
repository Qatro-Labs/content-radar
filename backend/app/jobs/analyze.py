"""Calcula las oportunidades a partir de las piezas recolectadas y las guarda por ejecución.

    uv run python -m app.jobs.analyze

clasificar cada pieza con Jev (cacheado) → quitar lo que no trata de IA → embed → cluster →
republicaciones con Jev (cacheado) → scores deterministas → audience fit con el LLM (cacheado) →
«por qué importa» con el LLM (cacheado) → verificación de sus afirmaciones con Jev (cacheado, con
JEV_VERIFY_CLAIMS) → persistir.
Sin TYPESAFE_API_KEY, o si Jev falla, las piezas quedan sin clasificar, los pares los decide la
regla de respaldo, con JEV_VERIFY_CLAIMS activo las afirmaciones sin veredicto se publican
marcadas como no verificadas, y el job sigue. Sin
LLM_API_KEY, o si el LLM falla en un tema, su audience fit queda en null (CLAUDE.md §2, regla 3).
"""

import asyncio
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.usage import UsageMeter
from app.core.config import Settings, get_settings
from app.db.session import SessionLocal, engine
from app.editorial.evaluator import build_evaluator
from app.editorial.explanation import build_explainer
from app.intelligence.jev import build_judge, to_piece_judgment
from app.intelligence.opportunities import TopicResult, rank
from app.models import PipelineRun
from app.services.audience_fit import FitStats, evaluate_topics
from app.services.classification import ClassificationStats, classify_pieces, load_judgments
from app.services.costs import record_meter
from app.services.explanation import ExplainStats, explain_topics
from app.services.opportunities import (
    ANALYZE_JOB,
    ComputedOpportunities,
    compute_opportunities,
    load_pieces,
    save_opportunities,
)
from app.services.replicas import ReplicaStats
from app.services.verification import VerifyStats, build_claim_verifier

log = structlog.get_logger()

LOCK_KEY = 0x0A7A1F2E  # clave de pg_advisory_lock para este job


@dataclass
class _Evaluated:
    jev: ClassificationStats
    fit: FitStats
    explain: ExplainStats
    computed: ComputedOpportunities
    results: list[TopicResult]


async def _evaluate(session: AsyncSession, run_id: int, as_of: datetime) -> _Evaluated:
    settings = get_settings()
    loaded = await load_pieces(session, as_of)
    # Un solo cliente de Jev para las dos baterías. El consumo de la de pieza se guarda antes de
    # seguir: si falla lo que viene después, ese gasto ya está hecho y debe constar.
    judge, piece_meter, pair_meter = build_judge(settings), UsageMeter(), UsageMeter()
    jev = await classify_pieces(session, loaded, judge=judge, meter=piece_meter)
    await record_meter(session, piece_meter, pipeline_run_id=run_id)
    answers = await load_judgments(session, loaded)
    judgments = {item_id: to_piece_judgment(item_id, a) for item_id, a in answers.items()}
    computed = await compute_opportunities(
        session, as_of, pieces=loaded, judgments=judgments, judge=judge, meter=pair_meter
    )
    await record_meter(session, pair_meter, pipeline_run_id=run_id)
    llm_meter = UsageMeter()
    results, fit, explain = await _fit_and_explain(
        session, computed.results, answers=answers, settings=settings, meter=llm_meter
    )
    await record_meter(session, llm_meter, pipeline_run_id=run_id)
    # El orden se decide después del audience fit: antes no hay Opportunity Score.
    return _Evaluated(jev, fit, explain, computed, rank(results))


async def _fit_and_explain(
    session: AsyncSession,
    results: list[TopicResult],
    *,
    answers: dict[int, dict[str, Any]],
    settings: Settings,
    meter: UsageMeter,
) -> tuple[list[TopicResult], FitStats, ExplainStats]:
    fitted, fit = await evaluate_topics(
        session, results, answers=answers, evaluator=build_evaluator(settings), meter=meter
    )
    # Después del fit y de la recomendación: el texto explica lo que ya calculó Python.
    explained, explain = await explain_topics(
        session,
        fitted,
        answers=answers,
        explainer=build_explainer(settings),
        meter=meter,
        verifier=build_claim_verifier(settings),
    )
    return explained, fit, explain


def _stats(as_of: datetime, e: _Evaluated) -> dict[str, Any]:
    return {
        "as_of": as_of.isoformat(),
        "pieces": e.computed.analyzed,
        "off_topic_removed": e.computed.off_topic_removed,
        "opportunities": len(e.results),
        "lifecycle": dict(Counter(r.opportunity.lifecycle.value for r in e.results)),
        "recommendation": dict(Counter(r.opportunity.recommendation.value for r in e.results)),
        "jev": asdict(e.jev),
        "replicas": asdict(e.computed.replicas),
        "llm": asdict(e.fit),
        "explain": asdict(e.explain),  # incluye `verification`
    }


async def _run(session: AsyncSession, run_row: PipelineRun) -> tuple[_Evaluated, dict[str, Any]]:
    as_of = datetime.now(UTC)
    evaluated = await _evaluate(session, run_row.id, as_of)
    await save_opportunities(session, run_row.id, evaluated.results)
    stats = _stats(as_of, evaluated)
    run_row.status, run_row.stats = "success", stats
    return evaluated, stats


def _print_summary(run_id: int, stats: dict[str, Any], evaluated: _Evaluated) -> None:
    jev, fit, explain, results = evaluated.jev, evaluated.fit, evaluated.explain, evaluated.results
    print(
        f"✓ run #{run_id}: {stats['pieces']} piezas · {len(results)} oportunidades · "
        f"{stats['lifecycle']}"
    )
    print(f"  filtro about_ai: {stats['off_topic_removed']} piezas fuera de tema quitadas")
    print(f"  jev: {jev.classified} clasificadas · {jev.cached} de caché · {jev.failed} fallidas")
    if jev.skipped_reason:
        print(f"  jev omitido: {jev.skipped_reason}")
    _print_replicas(evaluated.computed.replicas)
    print(
        f"  llm: {fit.evaluated} evaluados · {fit.cached} de caché · {fit.failed} fallidos · "
        f"{fit.without_evidence} sin piezas seguras"
    )
    if fit.skipped_reason:
        print(f"  llm omitido: {fit.skipped_reason}")
    print(
        f"  por qué importa: {explain.explained} redactados · {explain.cached} de caché · "
        f"{explain.failed} fallidos · {explain.without_fit} sin audience fit"
    )
    _print_verification(explain.verification)
    print(f"  recomendaciones: {stats['recommendation']}")
    for r in results[:10]:
        o = r.opportunity
        print(
            f"  {o.momentum_score:5.1f}  {o.lifecycle.value:12} acc {o.acceleration:+.2f}  "
            f"{o.source_count} fuentes  fit {o.audience_fit_score}  {o.recommendation.value:13} "
            f"{o.topic[:60]}"
        )


def _print_verification(v: VerifyStats | None) -> None:
    if v is None:
        print("  verificación jev: apagada (JEV_VERIFY_CLAIMS)")
        return
    print(
        f"  verificación jev: {v.verified} verificadas · {v.cached} de caché · "
        f"{v.rejected} rechazadas · {v.unverified_topics} temas sin verificar"
    )
    if v.skipped_reason:
        print(f"  verificación omitida: {v.skipped_reason}")


def _print_replicas(r: ReplicaStats) -> None:
    print(
        f"  republicaciones: {r.replicas} piezas ({r.unverified} sin verificar) · pares: "
        f"{r.candidates} candidatos · {r.judged} jev · {r.cached} de caché · {r.failed} fallidos · "
        f"{r.over_budget} fuera de presupuesto"
    )
    if r.skipped_reason:
        print(f"  pares omitidos: {r.skipped_reason}")


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
                evaluated, stats = await _run(session, run_row)
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
    _print_summary(run_row.id, stats, evaluated)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
