"""Acuerdo de Jev (batería de producción, respuestas guardadas en la DB) con una hoja de etiquetas.

Solo lee: busca cada pieza de la hoja por URL, carga sus juicios con `load_judgments` (misma
clave de caché que `analyze`) y compara las decisiones de `to_piece_judgment` con la hoja.
Uso, desde backend/:  PYTHONPATH=. uv run python ../data/evaluations/score_jev.py [--json]
"""

import asyncio
import csv
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.intelligence.jev import to_piece_judgment
from app.models import ContentItem, Source
from app.services.classification import load_judgments
from app.services.opportunities import _to_piece

# Por defecto, las etiquetas del evaluador LLM; `--sheet <archivo>` para otra hoja (p. ej. humana).
DEFAULT_SHEET = "jev_piece_v2_llm_labels.csv"
SHEET_NAME = sys.argv[sys.argv.index("--sheet") + 1] if "--sheet" in sys.argv else DEFAULT_SHEET
SHEET = Path(__file__).parent / SHEET_NAME
YES = {"si": True, "sí": True, "no": False}
# Columna de la hoja -> decisión de Jev. `relevant` no es una pregunta de Jev: se compara con lo que
# el pipeline usaría (trata de IA y de su uso en organizaciones).
CHECKS = {
    "about_ai": lambda j: j.about_ai,
    "business_use": lambda j: j.business_use,
    "latam_context": lambda j: j.latam_context,
    "business_case": lambda j: j.business_case,
    "relevant": lambda j: (
        False
        if j.about_ai is False or j.business_use is False
        else (True if j.about_ai and j.business_use else None)
    ),
}


def label(value: str) -> bool | None:
    return YES.get(value.strip().lower())


async def main() -> None:
    rows = [r for r in csv.DictReader(SHEET.open(encoding="utf-8")) if r["id"].isdigit()]
    async with SessionLocal() as s:
        found = (
            await s.execute(
                select(ContentItem, Source)
                .join(Source)
                .where(ContentItem.url.in_([r["url"] for r in rows]))
            )
        ).all()
        pieces = {i.url: _to_piece(i, src, [], as_of=datetime.now(UTC)) for i, src in found}
        answers = await load_judgments(s, list(pieces.values()))
    judged = {
        url: to_piece_judgment(p.item_id, answers[p.item_id])
        for url, p in pieces.items()
        if p.item_id in answers
    }
    print(
        f"modelo {get_settings().jev_model} · piezas en la hoja {len(rows)} · en la DB "
        f"{len(pieces)} · con juicio de Jev {len(judged)}\n"
    )
    report = {}
    for col, decide in CHECKS.items():
        pairs = [
            (label(r[col]), decide(judged[r["url"]]))
            for r in rows
            if label(r[col]) is not None and r["url"] in judged
        ]
        certain = [(h, m) for h, m in pairs if m is not None]
        hits = sum(h == m for h, m in certain)
        confusion = Counter(f"etiqueta={h} jev={m}" for h, m in certain if h != m)
        report[col] = {
            "labeled": len(pairs),
            "jev_certain": len(certain),
            "coverage": round(len(certain) / len(pairs), 2) if pairs else None,
            "agreement_when_certain": round(hits / len(certain), 2) if certain else None,
            "errors": dict(confusion),
        }
        if pairs:
            r = report[col]
            print(
                f"{col:14s} etiquetadas {len(pairs):2d} · Jev seguro en {len(certain):2d} "
                f"({r['coverage']:.0%}) · acuerdo {r['agreement_when_certain']}"
                f" · errores {dict(confusion)}"
            )
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=1))


asyncio.run(main())
