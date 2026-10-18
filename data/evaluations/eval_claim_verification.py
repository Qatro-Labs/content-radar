"""Validación de la batería `claim` de Jev con afirmaciones reales de «por qué importa» (D10 del
plan `intel-claim-verification`). Desde backend/:

  PYTHONPATH=. uv run python ../data/evaluations/eval_claim_verification.py sample \
      --out ../data/evaluations/jev_claim_v1_sample.csv
  PYTHONPATH=. uv run python ../data/evaluations/eval_claim_verification.py run \
      --variant facts|evidence_only --battery <batería.yaml> \
      --sample ../data/evaluations/jev_claim_v1_sample.csv \
      --out ../data/evaluations/jev_claim_v1_answers.json
  PYTHONPATH=. uv run python ../data/evaluations/eval_claim_verification.py score \
      --sample ../data/evaluations/jev_claim_v1_sample.csv \
      --answers ../data/evaluations/jev_claim_v1_answers.json

`sample` solo lee de la DB (`SET TRANSACTION READ ONLY` como primera sentencia) la ejecución de
`analyze` servida (`DEMO_RUN_ID` o la última correcta) y escribe el CSV: 40 afirmaciones reales
que pasaron Python y 10 negativas sintéticas (MOCK de evaluación, `synthetic=true`), con semilla
fija. `run` llama a Jev sin pasar por la DB ni por el service, se reanuda por `id` y no deja pasar
de 150 llamadas en total entre todas las tandas del JSON. `score` calcula los tres criterios de
D10 por tanda.
"""

import argparse
import asyncio
import csv
import json
import random
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.editorial.audience import MAX_DESCRIPTION_CHARS
from app.editorial.explanation import opportunity_facts
from app.intelligence.jev import (
    CLAIM_BATTERY,
    CitedEvidence,
    build_judge,
    claim_state,
    claim_supported,
    load_battery,
)
from app.models import ContentItem, LlmEvaluation, OpportunityRecord, PipelineRun, Source
from app.schemas.opportunity import Opportunity, OpportunityTimeline
from app.services.explanation import EXPLAIN_OPPORTUNITY_OPERATION
from app.services.opportunities import ANALYZE_JOB

SEED = 18
REAL_CLAIMS = 40
MIN_REAL_CLAIMS = 30  # menos, y la evaluación no dice nada (Riesgos del plan)
NEGATIVES_PER_KIND = 5
MAX_CLAIMS_PER_TOPIC = 3
MAX_TOTAL_CALLS = 150
SWAPPED_CITATION = "swapped_citation"
INSERTED_FACT = "inserted_fact"
NATURAL = "natural"
FACTS = "facts"
EVIDENCE_ONLY = "evidence_only"
# Hechos que no salen de ninguna pieza ni de los datos medidos: si Jev los respalda, no filtra.
INSERTED_FACTS = [
    ", según un estudio de McKinsey publicado esta semana",
    ", como ya hacen Bancolombia y Mercado Libre en sus equipos comerciales",
    ", y Gartner lo sitúa entre las tres prioridades de los directores de operaciones",
    ", tras el anuncio de Microsoft de integrarlo en todos sus productos para empresas",
    ", según una encuesta de Deloitte a directivos latinoamericanos",
]
COLUMNS = [
    "id",
    "opportunity_id",
    "recommendation",
    "position",
    "synthetic",
    "negative_kind",
    "claim",
    "measured_facts",
    "evidence_json",
    "label",
]
SUPPORTED_LABEL = "supported"
NEGATIVE_LABELS = {"unsupported", "contradicted"}
# Conserva, filtra y no vacía la demo (D10), fijados antes de ver respuestas de Jev.
KEEP_MIN = 0.70
FILTER_MIN = 0.60
TOPICS_WITH_TEXT_MIN = 0.80


@dataclass(frozen=True)
class ServedClaim:
    opportunity_id: str
    recommendation: str
    position: int  # 1-based, en el orden en que las devolvió el LLM
    claim: str
    facts: list[str]
    evidence: list[CitedEvidence]


def normalized(s: str) -> str:
    return " ".join(s.split())


async def served_run_id(session: AsyncSession) -> int:
    if (demo := get_settings().demo_run_id) is not None:
        return demo
    run_id = await session.scalar(
        select(PipelineRun.id)
        .where(PipelineRun.job == ANALYZE_JOB, PipelineRun.status == "success")
        .order_by(PipelineRun.id.desc())
        .limit(1)
    )
    if run_id is None:
        raise SystemExit("no hay ejecuciones correctas de analyze")
    return run_id


def served_claims_of(output: dict[str, Any], served: str) -> list[tuple[int, dict[str, Any]]]:
    claims = output.get("claims", [])
    return [(i, c) for i, c in enumerate(claims, start=1) if normalized(c["text"]) in served]


def best_match(rows: Sequence[dict[str, Any]], served: str) -> list[tuple[int, dict[str, Any]]]:
    # La fila de caché que dio el texto servido es la que más afirmaciones encaja en él.
    matches = [served_claims_of(r, served) for r in rows]
    return max(matches, key=len, default=[])


async def cited_pieces(session: AsyncSession, urls: set[str]) -> dict[str, CitedEvidence]:
    rows = await session.execute(
        select(ContentItem.url, Source.name, ContentItem.title, ContentItem.description)
        .join(Source)
        .where(ContentItem.url.in_(urls))
    )
    return {
        url: CitedEvidence(
            name, title, description[:MAX_DESCRIPTION_CHARS] if description else None
        )
        for url, name, title, description in rows.all()
    }


def claim_evidence(
    claim: dict[str, Any], topic_urls: set[str], pieces: dict[str, CitedEvidence]
) -> list[CitedEvidence]:
    # Como `_cited_evidence` del service: solo piezas del tema, sin repetir y en el orden de cita.
    urls = [u for u in dict.fromkeys(claim["evidence_urls"]) if u in topic_urls and u in pieces]
    return [pieces[u] for u in urls]


async def load_served_claims(session: AsyncSession) -> list[ServedClaim]:
    await session.execute(text("SET TRANSACTION READ ONLY"))
    run_id = await served_run_id(session)
    records = (
        await session.scalars(select(OpportunityRecord).where(OpportunityRecord.run_id == run_id))
    ).all()
    outputs = await explanation_outputs(session, [r.opportunity_id for r in records])
    matched = {
        r.opportunity_id: best_match(
            outputs[r.opportunity_id], normalized(r.payload["why_it_matters"])
        )
        for r in records
    }
    urls = {u for m in matched.values() for _, c in m for u in c["evidence_urls"]}
    pieces = await cited_pieces(session, urls) if urls else {}
    served = sum(map(len, matched.values()))
    print(f"ejecución {run_id}: {len(records)} oportunidades · {served} afirmaciones servidas")
    return [claim for r in records for claim in to_served(r, matched[r.opportunity_id], pieces)]


async def explanation_outputs(
    session: AsyncSession, opportunity_ids: list[str]
) -> defaultdict[str, list[dict[str, Any]]]:
    rows = await session.execute(
        select(LlmEvaluation.opportunity_id, LlmEvaluation.output).where(
            LlmEvaluation.operation == EXPLAIN_OPPORTUNITY_OPERATION,
            LlmEvaluation.opportunity_id.in_(opportunity_ids),
        )
    )
    outputs: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for opportunity_id, output in rows.all():
        outputs[opportunity_id].append(output)
    return outputs


def to_served(
    record: OpportunityRecord,
    matched: list[tuple[int, dict[str, Any]]],
    pieces: dict[str, CitedEvidence],
) -> list[ServedClaim]:
    o = Opportunity.model_validate(record.payload)
    facts = opportunity_facts(o, OpportunityTimeline.model_validate(record.timeline))
    topic_urls = {e["url"] for e in record.evidence}
    served = [
        ServedClaim(o.id, o.recommendation.value, position, c["text"], facts, ev)
        for position, c in matched
        if (ev := claim_evidence(c, topic_urls, pieces))
    ]
    return served


def stratified_topics(claims: Sequence[ServedClaim], rng: random.Random) -> list[str]:
    # Round-robin entre recomendaciones: cada una aporta temas por turnos hasta agotar.
    by_recommendation: defaultdict[str, list[str]] = defaultdict(list)
    for c in claims:
        topics = by_recommendation[c.recommendation]
        if c.opportunity_id not in topics:
            topics.append(c.opportunity_id)
    for topics in by_recommendation.values():
        rng.shuffle(topics)
    queues = [by_recommendation[k] for k in sorted(by_recommendation)]
    order: list[str] = []
    while any(queues):
        order += [q.pop(0) for q in queues if q]
    return order


def pick_real(claims: Sequence[ServedClaim], rng: random.Random) -> list[ServedClaim]:
    by_topic: defaultdict[str, list[ServedClaim]] = defaultdict(list)
    for c in claims:
        by_topic[c.opportunity_id].append(c)
    picked: list[ServedClaim] = []
    for topic in stratified_topics(claims, rng):
        picked += by_topic[topic][:MAX_CLAIMS_PER_TOPIC]
        if len(picked) >= REAL_CLAIMS:
            break
    return picked[:REAL_CLAIMS]


def synthetic_negatives(
    pool: Sequence[ServedClaim], rng: random.Random
) -> list[tuple[ServedClaim, str]]:
    # De afirmaciones reales que no están en la muestra; la cita cambiada viene de otro tema.
    chosen = rng.sample(list(pool), 2 * NEGATIVES_PER_KIND)
    swapped = []
    for c in chosen[:NEGATIVES_PER_KIND]:
        donor = rng.choice([d for d in pool if d.opportunity_id != c.opportunity_id])
        swapped.append((replace(c, evidence=donor.evidence), SWAPPED_CITATION))
    inserted = [
        (replace(c, claim=c.claim.rstrip(". ") + phrase + "."), INSERTED_FACT)
        for c, phrase in zip(chosen[NEGATIVES_PER_KIND:], INSERTED_FACTS, strict=True)
    ]
    return swapped + inserted


def csv_row(row_id: int, c: ServedClaim, kind: str = "") -> dict[str, Any]:
    return {
        "id": row_id,
        "opportunity_id": c.opportunity_id,
        "recommendation": c.recommendation,
        "position": c.position,
        "synthetic": "true" if kind else "false",
        "negative_kind": kind,
        "claim": c.claim,
        "measured_facts": json.dumps(c.facts, ensure_ascii=False),
        "evidence_json": json.dumps([asdict(e) for e in c.evidence], ensure_ascii=False),
        "label": "unsupported" if kind else "",
    }


async def load_claims() -> list[ServedClaim]:
    async with SessionLocal() as session:
        claims = await load_served_claims(session)
        await session.rollback()
    return claims


def sample(out: Path) -> None:
    claims = asyncio.run(load_claims())
    rng = random.Random(SEED)
    real = pick_real(claims, rng)
    if len(real) < MIN_REAL_CLAIMS:
        raise SystemExit(
            f"solo {len(real)} afirmaciones elegibles: menos de {MIN_REAL_CLAIMS}, se para"
        )
    sampled_topics = {c.opportunity_id for c in real}
    pool = [c for c in claims if c.opportunity_id not in sampled_topics]
    rows = [csv_row(i, c) for i, c in enumerate(real, start=1)]
    rows += [
        csv_row(len(rows) + i, c, k)
        for i, (c, k) in enumerate(synthetic_negatives(pool, rng), start=1)
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    synthetic = len(rows) - len(real)
    print(f"{len(real)} reales de {len(sampled_topics)} temas + {synthetic} sintéticas → {out}")


def read_sample(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def row_state(row: dict[str, str], variant: str) -> dict[str, Any]:
    evidence = [CitedEvidence(**e) for e in json.loads(row["evidence_json"])]
    state = claim_state(row["claim"], facts=json.loads(row["measured_facts"]), evidence=evidence)
    if variant == EVIDENCE_ONLY:
        del state["measured_facts"]
    return state


async def judge_rows(
    battery_path: Path, rows: list[dict[str, str]], variant: str
) -> dict[str, Any]:
    judge = build_judge(get_settings())
    if judge is None:
        raise SystemExit("falta TYPESAFE_API_KEY")
    battery = load_battery(CLAIM_BATTERY, battery_path)
    results = await asyncio.gather(
        *(judge.judge(row_state(r, variant), battery.questions) for r in rows)
    )
    return {
        r["id"]: {"model": res.model, "input_tokens": res.input_tokens, "answers": res.answers}
        for r, res in zip(rows, results, strict=True)
    }


def run(variant: str, battery_path: Path, sample_path: Path, out: Path) -> None:
    done: dict[str, dict[str, Any]] = json.loads(out.read_text()) if out.exists() else {}
    tanda = f"{battery_path.stem}:{variant}"
    answered = done.setdefault(tanda, {})
    missing = [r for r in read_sample(sample_path) if r["id"] not in answered]
    total = sum(len(t) for t in done.values())
    if total + len(missing) > MAX_TOTAL_CALLS:
        raise SystemExit(f"{total} + {len(missing)} llamadas pasarían de {MAX_TOTAL_CALLS}")
    print(f"llamadas a Jev: {len(missing)} · tanda {tanda} · modelo {get_settings().jev_model}")
    answered.update(asyncio.run(judge_rows(battery_path, missing, variant)))
    out.write_text(json.dumps(done, ensure_ascii=False, indent=1))
    print(f"guardadas {len(answered)} respuestas de {tanda} en {out}")


def share(hits: int, n: int) -> str:
    return f"{hits}/{n} ({hits / n:.0%})" if n else "0/0 (sin datos)"


def negative_kind(row: dict[str, str]) -> str:
    return row["negative_kind"] or NATURAL


def score_tanda(tanda: str, rows: list[dict[str, str]], answers: dict[str, Any]) -> None:
    verdict = {r["id"]: claim_supported(answers[r["id"]]["answers"]) for r in rows}
    supported = [r for r in rows if r["label"] == SUPPORTED_LABEL]
    negatives = [r for r in rows if r["label"] in NEGATIVE_LABELS]
    kept = sum(verdict[r["id"]] is True for r in supported)
    filtered = sum(verdict[r["id"]] is False for r in negatives)
    real = [r for r in rows if r["synthetic"] == "false"]
    topics = {r["opportunity_id"] for r in real}
    with_text = {r["opportunity_id"] for r in real if verdict[r["id"]] is True}
    print(f"\n== {tanda} ==")
    print_criterion("1. conserva", kept, len(supported), KEEP_MIN)
    print_criterion("2. filtra", filtered, len(negatives), FILTER_MIN)
    print_criterion("3. temas con texto", len(with_text), len(topics), TOPICS_WITH_TEXT_MIN)
    for kind in (SWAPPED_CITATION, INSERTED_FACT, NATURAL):
        of_kind = [r for r in negatives if negative_kind(r) == kind]
        rejected = sum(verdict[r["id"]] is False for r in of_kind)
        print(f"   filtra {kind}: {share(rejected, len(of_kind))}")
    print_breakdowns(rows, verdict)


def print_criterion(name: str, hits: int, n: int, minimum: float) -> None:
    ok = n > 0 and hits / n >= minimum
    print(f"{name}: {share(hits, n)} · mínimo {minimum:.0%} · {'cumple' if ok else 'NO cumple'}")


def print_breakdowns(rows: list[dict[str, str]], verdict: dict[str, bool | None]) -> None:
    for position in sorted({r["position"] for r in rows if r["synthetic"] == "false"}):
        of_position = [
            r for r in rows if r["position"] == position and r["label"] == SUPPORTED_LABEL
        ]
        kept = sum(verdict[r["id"]] is True for r in of_position)
        print(f"   conserva posición {position}: {share(kept, len(of_position))}")
    matrix = Counter((r["label"], verdict[r["id"]]) for r in rows)
    print("   etiqueta × veredicto (True publica, False rechaza, None sin juicio):")
    for (label, v), n in sorted(matrix.items(), key=str):
        print(f"     {label:12} {v!s:5} {n}")


def score(sample_path: Path, answers_path: Path) -> None:
    rows = read_sample(sample_path)
    if unlabelled := [r["id"] for r in rows if not r["label"]]:
        raise SystemExit(f"filas sin etiqueta: {unlabelled}")
    done = json.loads(answers_path.read_text())
    for tanda, answers in done.items():
        tokens = sum(a["input_tokens"] or 0 for a in answers.values())
        print(f"\n{tanda}: {len(answers)} llamadas · {tokens} tokens de entrada")
        score_tanda(tanda, [r for r in rows if r["id"] in answers], answers)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["sample", "run", "score"])
    parser.add_argument("--variant", choices=[FACTS, EVIDENCE_ONLY])
    parser.add_argument("--battery", type=Path)
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--answers", type=Path)
    args = parser.parse_args()
    if args.command == "sample":
        sample(args.out)
    elif args.command == "run":
        run(args.variant, args.battery, args.sample, args.out)
    else:
        score(args.sample, args.answers)


if __name__ == "__main__":
    main()
