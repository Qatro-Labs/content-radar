"""Llama a Jev con una batería sobre las piezas de unas hojas de etiquetas, y puntúa sus `noul`.

A diferencia de `score_jev.py` (que lee los juicios guardados de la batería de producción), este
script sirve para comparar baterías candidatas sin escribir en la DB: lee las piezas por URL, llama
a Jev y guarda las respuestas en un JSON. Desde backend/:

  PYTHONPATH=. uv run python ../data/evaluations/eval_jev_battery.py run \
      --battery <batería.yaml> --sheet <hoja.csv> [--sheet ...] --out <respuestas.json>
  PYTHONPATH=. uv run python ../data/evaluations/eval_jev_battery.py score \
      --answers <respuestas.json> --sheet <hoja.csv> [--sheet ...] --map about_ai=about_ai ... \
      [--filter about_ai+ai_in_title ...]

`run` solo pide las piezas que no están ya en `--out` (se puede reanudar). `--map` empareja una
columna de la hoja con una pregunta `noul` de las respuestas. `--filter` cuenta, contra la columna
`about_ai`, lo que quitaría el filtro de ruido si sale la pieza cuando todas esas preguntas dicen
"no" con seguridad.
"""

import argparse
import asyncio
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.intelligence.jev import (
    NOUL_NO,
    NOUL_YES,
    Battery,
    build_judge,
    load_battery,
    piece_state,
)
from app.models import ContentItem, Source
from app.services.opportunities import _to_piece

YES = {"si": True, "sí": True, "no": False}
FILTER_COLUMN = "about_ai"


def sheet_rows(paths: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with Path(path).open(encoding="utf-8") as f:
            # La hoja de la v2 lleva una fila de instrucciones sin id numérico.
            rows += [r for r in csv.DictReader(f) if r.get("id", "0").isdigit()]
    return rows


async def judge_missing(battery: Battery, sheets: list[str], done: dict[str, Any]) -> None:
    urls = [r["url"] for r in sheet_rows(sheets) if r["url"] not in done]
    async with SessionLocal() as s:
        found = (
            await s.execute(
                select(ContentItem, Source).join(Source).where(ContentItem.url.in_(urls))
            )
        ).all()
        await s.rollback()
    states = {
        i.url: piece_state(_to_piece(i, src, [], as_of=datetime.now(UTC))) for i, src in found
    }
    judge = build_judge(get_settings())
    if judge is None:
        raise SystemExit("falta TYPESAFE_API_KEY")
    print(f"llamadas a Jev: {len(states)} · modelo {get_settings().jev_model}")
    results = await asyncio.gather(*(judge.judge(st, battery.questions) for st in states.values()))
    for url, r in zip(states, results, strict=True):
        done[url] = {"model": r.model, "input_tokens": r.input_tokens, "answers": r.answers}


def run(battery_path: str, sheets: list[str], out: Path) -> None:
    done = json.loads(out.read_text()) if out.exists() else {}
    asyncio.run(judge_missing(load_battery("piece", Path(battery_path)), sheets, done))
    out.write_text(json.dumps(done, ensure_ascii=False, indent=1))
    print(f"guardadas {len(done)} piezas en {out}")


def decide(p: float) -> bool | None:
    if p >= NOUL_YES:
        return True
    if p <= NOUL_NO:
        return False
    return None


def labelled(rows: list[dict[str, str]], column: str) -> list[dict[str, str]]:
    return [r for r in rows if r[column].strip().lower() in YES]


def score_question(rows: list[dict[str, str]], answers: dict, column: str, question: str) -> None:
    pairs = [
        (YES[r[column].strip().lower()], decide(answers[r["url"]]["answers"][question]["noul"]))
        for r in labelled(rows, column)
    ]
    certain = [(label, jev) for label, jev in pairs if jev is not None]
    hits = sum(label == jev for label, jev in certain)
    false_yes = sum(label is False and jev is True for label, jev in certain)
    false_no = sum(label is True and jev is False for label, jev in certain)
    print(
        f"{column}={question}: etiquetadas {len(pairs)} · seguras {len(certain)} "
        f"({len(certain) / len(pairs):.0%}) · acuerdo {hits}/{len(certain)} "
        f"({hits / len(certain):.0%}) · falso sí {false_yes} · falso no {false_no}"
    )


def score_filter(rows: list[dict[str, str]], answers: dict, questions: list[str]) -> None:
    # Como `keep_about_ai`: la pieza sale solo si todas las preguntas dicen "no" con seguridad.
    dropped = [
        YES[r[FILTER_COLUMN].strip().lower()]
        for r in labelled(rows, FILTER_COLUMN)
        if all(decide(answers[r["url"]]["answers"][q]["noul"]) is False for q in questions)
    ]
    off_topic = dropped.count(False)
    print(
        f"filtro {' y '.join(questions)}: quita {len(dropped)} etiquetadas "
        f"({off_topic} fuera de tema, {len(dropped) - off_topic} buenas)"
    )


def score(answers_path: str, sheets: list[str], mapping: list[str], filters: list[str]) -> None:
    answers = json.loads(Path(answers_path).read_text())
    rows = [r for r in sheet_rows(sheets) if r["url"] in answers]
    print(f"piezas con respuesta y etiqueta: {len(rows)}")
    for pair in mapping:
        column, question = pair.split("=")
        score_question(rows, answers, column, question)
    for spec in filters:
        score_filter(rows, answers, spec.split("+"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run", "score"])
    parser.add_argument("--battery")
    parser.add_argument("--sheet", action="append", required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--answers")
    parser.add_argument("--map", action="append", default=[])
    parser.add_argument("--filter", action="append", default=[])
    args = parser.parse_args()
    if args.command == "run":
        run(args.battery, args.sheet, args.out)
    else:
        score(args.answers, args.sheet, args.map, args.filter)


main()
