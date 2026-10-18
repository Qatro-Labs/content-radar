"""Adopción del prompt `explain_opportunity.v2` con `claim.v2` y umbral 0,6, según el pre-registro
`jev_claim_adoption_prereg.md`. Desde backend/:

  PYTHONPATH=. uv run python ../data/evaluations/eval_explain_v2.py generate --run-id N \\
      --outputs ../data/evaluations/jev_claim_adoption_outputs.json
  PYTHONPATH=. uv run python ../data/evaluations/eval_explain_v2.py sample \\
      --outputs ../data/evaluations/jev_claim_adoption_outputs.json \\
      --sample ../data/evaluations/jev_claim_adoption_sample.csv
  # etiquetar el CSV y commitearlo antes de seguir
  PYTHONPATH=. uv run python ../data/evaluations/eval_explain_v2.py judge --outputs … --sample … \\
      --answers ../data/evaluations/jev_claim_adoption_answers.json
  PYTHONPATH=. uv run python ../data/evaluations/eval_explain_v2.py score --outputs … --sample … \\
      --answers …

`generate` lee la ejecución fijada en solo lectura (`SET TRANSACTION READ ONLY`), construye las
entradas como los briefs y llama al LLM con el prompt v2 sin pasar por `explain_topics`: no
escribe en la DB. `judge` se niega a correr con filas sin etiqueta.
"""

import argparse
import asyncio
import hashlib
import json
import math
import random
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from eval_claim_verification import (
    COLUMNS,
    FACTS,
    FILTER_MIN,
    INSERTED_FACT,
    KEEP_MIN,
    MIN_REAL_CLAIMS,
    NATURAL,
    NEGATIVE_LABELS,
    SEED,
    SUPPORTED_LABEL,
    SWAPPED_CITATION,
    TOPICS_WITH_TEXT_MIN,
    ServedClaim,
    best_match,
    csv_row,
    explanation_outputs,
    negative_kind,
    normalized,
    pick_real,
    read_sample,
    row_state,
    synthetic_negatives,
)
from sqlalchemy import select, text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.editorial.audience import MAX_PIECES, evidence_piece, safe_label
from app.editorial.evaluator import LLM_CONCURRENCY, EvaluationError, StructuredLlm
from app.editorial.explanation import (
    PROMPTS_DIR,
    ExplainInput,
    OpportunityExplanation,
    fit_notes,
    opportunity_facts,
    user_message,
)
from app.intelligence.explanation import ClaimDraft, known_numbers, python_checked
from app.intelligence.jev import (
    CLAIM_BATTERY,
    SUPPORT_QUESTION,
    SUPPORTS,
    CitedEvidence,
    build_judge,
    claim_state,
    excluded_from_llm,
    load_battery,
)
from app.models import OpportunityRecord, PipelineRun
from app.services.classification import load_judgments
from app.services.opportunities import ANALYZE_JOB, _served, load_evidence_pieces

PROMPT_FILE = PROMPTS_DIR / "explain_opportunity.v2.md"
BATTERY_FILE = PROMPTS_DIR / "jev/claim.v2.yaml"
MIN_CONFIDENCE = 0.6  # el del candidato pre-registrado
POSITION_WHY = 2
CLAIMS_PER_OUTPUT = 3
GUARD_TOLERANCE = 0.10
MAX_LLM_CALLS = 80
MAX_JEV_CALLS = 300
Z95 = 1.959964
REV_SUFFIX = "_rev"
LLM_FIELDS = ("output", "error", "input_tokens", "output_tokens")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- generate ---------------------------------------------------------------------------------


async def load_inputs(run_id: int) -> dict[str, dict[str, Any]]:
    topics: dict[str, dict[str, Any]] = {}
    async with SessionLocal() as session:
        await session.execute(text("SET TRANSACTION READ ONLY"))
        run = await session.get(PipelineRun, run_id)
        if run is None or run.job != ANALYZE_JOB or run.status != "success":
            raise SystemExit(f"la ejecución {run_id} no es un analyze correcto")
        records = (
            await session.scalars(
                select(OpportunityRecord).where(OpportunityRecord.run_id == run_id)
            )
        ).all()
        v1_outputs = await explanation_outputs(session, [r.opportunity_id for r in records])
        now = datetime.now(UTC)
        for r in records:
            served = _served(r)
            o = served.opportunity
            if not o.audience_fit_criteria:
                continue
            found = await load_evidence_pieces(session, served.evidence, as_of=now)
            answers = await load_judgments(session, [p for p, _ in found])
            safe = [p for p, _ in found if not excluded_from_llm(answers.get(p.item_id, {}))]
            safe = safe[:MAX_PIECES]
            if not safe:
                continue
            explain = ExplainInput(
                label=safe_label(o.topic, safe),
                facts=opportunity_facts(o, served.timeline),
                fit=fit_notes(o),
                pieces=[evidence_piece(p) for p in safe],
            )
            matched = best_match(v1_outputs[o.id], normalized(o.why_it_matters))
            topics[o.id] = {
                "recommendation": o.recommendation.value,
                "v1_positions": [position for position, _ in matched],
                "explain": explain,
            }
        await session.rollback()
    return topics


def explain_to_json(explain: ExplainInput) -> dict[str, Any]:
    return {
        "label": explain.label,
        "facts": explain.facts,
        "pieces": [
            {"url": p.url, "source": p.source, "title": p.title, "description": p.description}
            for p in explain.pieces
        ],
    }


async def call_llm(llm: StructuredLlm, explain: ExplainInput, system: str) -> dict[str, Any]:
    try:
        result = await llm.complete(
            system=system, user=user_message(explain), output_type=OpportunityExplanation
        )
    except EvaluationError as e:
        return {"error": str(e)}
    return {
        "output": result.output.model_dump(),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }


def generate(run_id: int, out: Path) -> None:
    settings = get_settings()
    done: dict[str, Any] = json.loads(out.read_text()) if out.exists() else {}
    if done and done["run_id"] != run_id:
        raise SystemExit(f"{out} es de la ejecución {done['run_id']}")
    topics = asyncio.run(load_inputs(run_id))
    previous = done.get("topics", {})
    pending = [k for k in topics if "output" not in previous.get(k, {})]
    calls = done.get("llm_calls", 0)
    if calls + len(pending) > MAX_LLM_CALLS:
        raise SystemExit(f"{calls} + {len(pending)} llamadas al LLM pasarían de {MAX_LLM_CALLS}")
    print(f"ejecución {run_id}: {len(topics)} temas · {len(pending)} llamadas al LLM")
    llm = StructuredLlm(
        AsyncAnthropic(api_key=settings.llm_api_key),
        settings.llm_model,
        asyncio.Semaphore(LLM_CONCURRENCY),
    )
    system = PROMPT_FILE.read_text(encoding="utf-8")

    async def run_all() -> list[dict[str, Any]]:
        return await asyncio.gather(*(call_llm(llm, topics[k]["explain"], system) for k in pending))

    results = dict(zip(pending, asyncio.run(run_all()), strict=True))
    out_topics = {}
    for key, t in topics.items():
        response = results[key] if key in results else previous[key]
        out_topics[key] = {
            "recommendation": t["recommendation"],
            "v1_positions": t["v1_positions"],
            **explain_to_json(t["explain"]),
            **{k: v for k, v in response.items() if k in LLM_FIELDS},
        }
    payload = {
        "run_id": run_id,
        "llm_model": settings.llm_model,
        "prompt_sha256": sha256(PROMPT_FILE),
        "llm_calls": calls + len(pending),
        "topics": out_topics,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    failed = sum("error" in r for r in results.values())
    print(f"guardadas {len(out_topics)} salidas en {out} · fallos del LLM: {failed}")


# --- claims de v2 -----------------------------------------------------------------------------


def claim_key(opportunity_id: str, position: int) -> str:
    return f"{opportunity_id}#{position}"


def valid_v2_claims(topic_id: str, t: Mapping[str, Any]) -> list[ServedClaim]:
    if "output" not in t:
        return []
    by_url = {p["url"]: p for p in t["pieces"]}
    texts = [f"{p['title']} {p['description'] or ''}" for p in t["pieces"]]
    numbers = known_numbers(["\n".join(t["facts"]), *texts])
    claims = []
    for position, c in enumerate(t["output"]["claims"], start=1):
        draft = ClaimDraft(c["text"], c["evidence_urls"])
        if not python_checked([draft], sent_urls=set(by_url), numbers=numbers):
            continue
        cited = [by_url[u] for u in dict.fromkeys(c["evidence_urls"]) if u in by_url]
        evidence = [CitedEvidence(p["source"], p["title"], p["description"]) for p in cited]
        claims.append(
            ServedClaim(topic_id, t["recommendation"], position, c["text"], t["facts"], evidence)
        )
    return claims


def all_valid_claims(outputs: Mapping[str, Any]) -> list[ServedClaim]:
    return [c for k, t in outputs["topics"].items() for c in valid_v2_claims(k, t)]


def load_outputs(path: Path) -> dict[str, Any]:
    outputs = json.loads(path.read_text())
    if outputs["prompt_sha256"] != sha256(PROMPT_FILE):
        raise SystemExit("el prompt v2 cambió desde que se generaron las salidas")
    return outputs


# --- sample -----------------------------------------------------------------------------------


def sample(outputs_path: Path, out: Path) -> None:
    import csv

    claims = all_valid_claims(load_outputs(outputs_path))
    rng = random.Random(SEED)
    real = pick_real(claims, rng)
    if len(real) < MIN_REAL_CLAIMS:
        raise SystemExit(f"solo {len(real)} afirmaciones v2 válidas: menos de {MIN_REAL_CLAIMS}")
    sampled = {c.opportunity_id for c in real}
    pool = [c for c in claims if c.opportunity_id not in sampled]
    rows = [csv_row(i, c) for i, c in enumerate(real, start=1)]
    rows += [
        csv_row(len(rows) + i, c, k)
        for i, (c, k) in enumerate(synthetic_negatives(pool, rng), start=1)
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(
        f"{len(real)} reales de {len(sampled)} temas + {len(rows) - len(real)} sintéticas → {out}"
    )


# --- judge ------------------------------------------------------------------------------------


def row_key(row: Mapping[str, str]) -> str:
    if row["synthetic"] == "true":
        return f"neg#{row['id']}"
    return claim_key(row["opportunity_id"], int(row["position"]))


def judge_states(outputs: Mapping[str, Any], rows: Sequence[dict[str, str]]) -> dict[str, Any]:
    states = {
        claim_key(c.opportunity_id, c.position): claim_state(
            c.claim, facts=c.facts, evidence=c.evidence
        )
        for c in all_valid_claims(outputs)
    }
    for row in rows:
        if row["synthetic"] == "true":
            states[row_key(row)] = row_state(row, FACTS)
    return states


def judge(outputs_path: Path, sample_path: Path, out: Path) -> None:
    rows = read_sample(sample_path)
    if unlabelled := [r["id"] for r in rows if not r["label"]]:
        raise SystemExit(f"filas sin etiqueta: {unlabelled}. Etiquetar y commitear antes de Jev")
    states = judge_states(load_outputs(outputs_path), rows)
    done: dict[str, Any] = json.loads(out.read_text()) if out.exists() else {}
    missing = [k for k in states if k not in done]
    if len(done) + len(missing) > MAX_JEV_CALLS:
        raise SystemExit(f"{len(done)} + {len(missing)} llamadas pasarían de {MAX_JEV_CALLS}")
    settings = get_settings()
    client = build_judge(settings)
    if client is None:
        raise SystemExit("falta TYPESAFE_API_KEY")
    battery = load_battery(CLAIM_BATTERY, BATTERY_FILE)
    print(f"llamadas a Jev: {len(missing)} · {BATTERY_FILE.name} · modelo {settings.jev_model}")

    async def run_all() -> list[Any]:
        return await asyncio.gather(
            *(client.judge(states[k], battery.questions) for k in missing),
            return_exceptions=True,
        )

    for key, res in zip(missing, asyncio.run(run_all()), strict=True):
        if isinstance(res, BaseException):
            print(f"  fallo de Jev en {key}: {type(res).__name__}")
            continue
        done[key] = {"model": res.model, "input_tokens": res.input_tokens, "answers": res.answers}
    out.write_text(json.dumps(done, ensure_ascii=False, indent=1))
    print(f"guardadas {len(done)} respuestas en {out}")


# --- score ------------------------------------------------------------------------------------


def supported(answers: Mapping[str, Any] | None) -> bool | None:
    # `claim_supported` con el umbral del candidato (0,6), sin tocar la constante del código.
    if answers is None:
        return None
    answer = answers.get(SUPPORT_QUESTION)
    reverse = answers.get(SUPPORT_QUESTION + REV_SUFFIX)
    if answer is None or reverse is None:
        return None
    return (
        answer["choice"] == SUPPORTS
        and answer["confidence"] >= MIN_CONFIDENCE
        and reverse["choice"] == SUPPORTS
    )


def wilson(hits: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = hits / n
    denominator = 1 + Z95**2 / n
    centre = (p + Z95**2 / (2 * n)) / denominator
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95**2 / (4 * n**2)) / denominator
    return (centre - half, centre + half)


def share(hits: int, n: int) -> str:
    if not n:
        return "0/0 (sin datos)"
    low, high = wilson(hits, n)
    return f"{hits}/{n} ({hits / n:.0%}; Wilson 95 % {low:.0%}–{high:.0%})"


def criterion(name: str, hits: int, n: int, minimum: float) -> bool:
    ok = n > 0 and hits / n >= minimum
    print(f"{name}: {share(hits, n)} · mínimo {minimum:.0%} · {'cumple' if ok else 'NO cumple'}")
    return ok


def score(outputs_path: Path, sample_path: Path, answers_path: Path) -> None:
    outputs = load_outputs(outputs_path)
    rows = read_sample(sample_path)
    answers = json.loads(answers_path.read_text())
    verdict = {k: supported(a["answers"]) for k, a in answers.items()}

    print(f"== D10 sobre la muestra (umbral {MIN_CONFIDENCE}) ==")
    by_row = {r["id"]: verdict.get(row_key(r)) for r in rows}
    pos = [r for r in rows if r["label"] == SUPPORTED_LABEL]
    neg = [r for r in rows if r["label"] in NEGATIVE_LABELS]
    keep = criterion("1. conserva", sum(by_row[r["id"]] is True for r in pos), len(pos), KEEP_MIN)
    filt = criterion("2. filtra", sum(by_row[r["id"]] is False for r in neg), len(neg), FILTER_MIN)
    real = [r for r in rows if r["synthetic"] == "false"]
    topics = {r["opportunity_id"] for r in real}
    with_text = {r["opportunity_id"] for r in real if by_row[r["id"]] is True}
    texts = criterion("3. temas con texto", len(with_text), len(topics), TOPICS_WITH_TEXT_MIN)
    for kind in (SWAPPED_CITATION, INSERTED_FACT, NATURAL):
        of_kind = [r for r in neg if negative_kind(r) == kind]
        rejected = sum(by_row[r["id"]] is False for r in of_kind)
        print(f"   filtra {kind}: {share(rejected, len(of_kind))}")
    for position in ("1", "2", "3"):
        of_position = [r for r in pos if r["position"] == position]
        kept = sum(by_row[r["id"]] is True for r in of_position)
        print(f"   conserva posición {position}: {share(kept, len(of_position))}")
    missing = sum(v is None for v in by_row.values())
    print(f"   sin veredicto en la muestra: {missing}")
    labels = {
        lab: sum(r["label"] == lab for r in real)
        for lab in ("supported", "unsupported", "contradicted")
    }
    print(f"   etiquetas reales: {labels}")

    print("\n== Guard de cobertura de la posición 2 (todos los temas) ==")
    # Temas con explicación v1 (el texto servido lleva afirmaciones del LLM) y v2 (hay salida).
    both = {k: t for k, t in outputs["topics"].items() if t["v1_positions"] and "output" in t}
    excluded = len(outputs["topics"]) - len(both)
    print(f"temas sin explicación v1 servida o sin salida v2 (fuera de N): {excluded}")
    n = len(both)
    v1 = sum(POSITION_WHY in t["v1_positions"] for t in both.values())
    a = b = 0
    for key, t in both.items():
        if len(t["output"]["claims"]) != CLAIMS_PER_OUTPUT:
            continue
        valid = {c.position for c in valid_v2_claims(key, t)}
        if POSITION_WHY in valid:
            a += 1
            b += verdict.get(claim_key(key, POSITION_WHY)) is True
    allowed = math.ceil(GUARD_TOLERANCE * n)
    print(f"N = {n} temas · tolerancia {allowed} temas")
    print(f"v1 llena (servido): {share(v1, n)}")
    guard_a = a >= v1 - allowed
    guard_b = b >= v1 - allowed
    print(f"guard A, v2 tras Python: {share(a, n)} · {'pasa' if guard_a else 'NO pasa'}")
    print(f"guard B, v2 tras Python y Jev: {share(b, n)} · {'pasa' if guard_b else 'NO pasa'}")

    all_claims = all_valid_claims(outputs)
    published = {
        c.opportunity_id
        for c in all_claims
        if verdict.get(claim_key(c.opportunity_id, c.position)) is True
    }
    print(f"temas con texto tras Jev (todos): {share(len(published), n)}")
    kept_all = sum(verdict.get(claim_key(c.opportunity_id, c.position)) is True for c in all_claims)
    print(f"afirmaciones v2 publicadas tras Jev (todas): {share(kept_all, len(all_claims))}")
    v2_outputs = [t for t in outputs["topics"].values() if "output" in t]
    sizes = [len(t["output"]["claims"]) for t in v2_outputs]
    print(f"salidas v2: {len(v2_outputs)} de {n} · afirmaciones por salida: {sorted(set(sizes))}")

    llm_in = sum(t.get("input_tokens", 0) for t in v2_outputs)
    llm_out = sum(t.get("output_tokens", 0) for t in v2_outputs)
    jev_in = sum(a_["input_tokens"] or 0 for a_ in answers.values())
    print(
        f"\ncoste: LLM {outputs['llm_calls']} llamadas, {llm_in} + {llm_out} tokens · "
        f"Jev {len(answers)} llamadas, {jev_in} tokens de entrada"
    )
    adopt_prompt = guard_a
    adopt_flag = keep and filt and texts and guard_b
    yes_no = {True: "sí", False: "no"}
    print(f"\nDECISIÓN: prompt v2 {yes_no[adopt_prompt]} · flag {yes_no[adopt_flag]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["generate", "sample", "judge", "score"])
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--answers", type=Path)
    args = parser.parse_args()
    if args.command == "generate":
        generate(args.run_id, args.outputs)
    elif args.command == "sample":
        sample(args.outputs, args.sample)
    elif args.command == "judge":
        judge(args.outputs, args.sample, args.answers)
    else:
        score(args.outputs, args.sample, args.answers)


if __name__ == "__main__":
    main()
