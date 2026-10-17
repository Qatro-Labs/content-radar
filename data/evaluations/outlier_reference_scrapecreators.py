"""Tasa de outliers por plataforma y por referencia (mediana, p75, p90), con datos reales.

Solo lee la DB (transacción READ ONLY): no llama a ninguna API ni escribe nada. Usa las mismas
piezas y juicios de Jev en caché que `analyze` (`load_pieces`, `load_judgments`,
`keep_about_ai`) y las mismas reglas de referencia (`_performance`,
`_old_enough_for_reference`, `outliers.outlier_ratio`, `MIN_REFERENCE`). El cuantil se pasa
explícito para poder comparar opciones sin tocar las constantes.

Dos modos de referencia, para que la decisión valga con y sin el PR #48:
- `main`: la referencia son las piezas que pasan `keep_about_ai` (lo que hace `analyze` hoy).
- `#48`: la referencia son todas las piezas cargadas; los ratios se dan solo a las que pasan.

Desde backend/:
    PYTHONPATH=. uv run python ../data/evaluations/outlier_reference_scrapecreators.py \
        --as-of 2026-10-17T22:04:38+00:00
"""

import argparse
import asyncio
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import numpy as np
from sqlalchemy import text

from app.db.session import SessionLocal
from app.intelligence import outliers as out
from app.intelligence.jev import keep_about_ai, to_piece_judgment
from app.intelligence.opportunities import Piece, _old_enough_for_reference, _performance
from app.schemas.signal import Platform
from app.services.classification import load_judgments
from app.services.opportunities import load_pieces

PLATFORMS = [
    Platform.TIKTOK,
    Platform.REDDIT,
    Platform.HACKERNEWS,
    Platform.INSTAGRAM,
    Platform.YOUTUBE,
]
QUANTILES = {"mediana": 0.5, "p75": 0.75, "p90": 0.9}
TOP_TITLES = 8
GROUPED = {Platform.TIKTOK, Platform.REDDIT, Platform.INSTAGRAM}


def ratios_with(
    pieces: Sequence[Piece], reference: Sequence[Piece], as_of: datetime, quantile: float
) -> dict[int, float | None]:
    """Igual que `outlier_ratios`, con el cuantil explícito y la referencia aparte."""
    by_source: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for p in reference:
        value = _performance(p)
        if value is not None and _old_enough_for_reference(p, as_of):
            by_source[p.source_id].append((p.item_id, value))
    ratios: dict[int, float | None] = {}
    for p in pieces:
        value = _performance(p)
        if value is None:
            ratios[p.item_id] = None
            continue
        others = [v for item_id, v in by_source[p.source_id] if item_id != p.item_id]
        ratios[p.item_id] = out.outlier_ratio(value, others, quantile)
    return ratios


def _share(count: int, total: int) -> str:
    return f"{count} ({count / total:.0%})" if total else "—"


def _rates(pieces: list[Piece], reference: list[Piece], as_of: datetime, label: str) -> None:
    print(f"\n## Tasas ({label})")
    print("| plataforma | referencia | n con métrica | sin referencia | ≥2× | ≥3× |")
    print("|---|---|---|---|---|---|")
    flagged: dict[tuple[Platform, str], list[tuple[float, Piece]]] = {}
    for platform in PLATFORMS:
        group = [p for p in pieces if p.platform is platform and _performance(p) is not None]
        for qname, q in QUANTILES.items():
            ratios = ratios_with(group, reference, as_of, q)
            with_ref = [(r, p) for p in group if (r := ratios[p.item_id]) is not None]
            notable = sum(r >= out.NOTABLE_RATIO for r, _ in with_ref)
            outlier = sum(r >= out.OUTLIER_RATIO for r, _ in with_ref)
            print(
                f"| {platform.value} | {qname} | {len(group)} | {len(group) - len(with_ref)}"
                f" | {_share(notable, len(with_ref))} | {_share(outlier, len(with_ref))} |"
            )
            flagged[(platform, qname)] = sorted(
                ((r, p) for r, p in with_ref if r >= out.OUTLIER_RATIO), key=lambda x: -x[0]
            )
    print(f"\n## Piezas ≥3× por opción ({label})")
    for (platform, qname), items in flagged.items():
        if platform in (Platform.HACKERNEWS, Platform.YOUTUBE):
            continue
        print(f"\n### {platform.value} · {qname}: {len(items)}")
        for r, p in items[:TOP_TITLES]:
            print(f"- {r:.1f}× · {p.source_name} · {p.title[:90]!r}")


def _groups(pieces: list[Piece], reference: list[Piece], as_of: datetime, label: str) -> None:
    print(f"\n## Referencias por fuente ({label})")
    print("| plataforma | fuente | piezas | en referencia | mediana | p75 | p90 | máx/mediana |")
    print("|---|---|---|---|---|---|---|---|")
    scored: dict[int, list[Piece]] = defaultdict(list)
    for p in pieces:
        if p.platform in GROUPED:
            scored[p.source_id].append(p)
    for source_id, group in sorted(scored.items(), key=lambda kv: kv[1][0].source_name):
        ref = [
            v
            for p in reference
            if p.source_id == source_id
            and (v := _performance(p)) is not None
            and _old_enough_for_reference(p, as_of)
        ]
        cells = "| — | — | — | — |"
        if len(ref) >= out.MIN_REFERENCE:
            q = np.quantile(ref, [0.5, 0.75, 0.9])
            spread = f"{max(ref) / q[0]:.1f}" if q[0] > 0 else "—"
            cells = f"| {q[0]:,.0f} | {q[1]:,.0f} | {q[2]:,.0f} | {spread} |"
        first = group[0]
        print(f"| {first.platform.value} | {first.source_name} | {len(group)} | {len(ref)} {cells}")


def _tiktok_age(pieces: list[Piece], as_of: datetime) -> None:
    tiktok = [p for p in pieces if p.platform is Platform.TIKTOK and _performance(p) is not None]
    if not tiktok:
        return
    ages = np.array([(as_of - p.published_at) / timedelta(days=1) for p in tiktok])
    perf = np.array([_performance(p) for p in tiktok], dtype=float)
    print("\n## TikTok: edad y views/día")
    print(f"edad (días) p10/p50/p90: {np.quantile(ages, [0.1, 0.5, 0.9]).round(1)}")
    print(f"edad máxima: {ages.max():.1f} días")
    print(f"con < 2 días (fuera de la referencia): {(ages < 2).sum()} de {len(ages)}")
    print(f"views/día p10/p50/p90: {np.quantile(perf, [0.1, 0.5, 0.9]).round(0)}")
    for lo, hi in [(0, 2), (2, 4), (4, 7), (7, 30)]:
        sel = (ages >= lo) & (ages < hi)
        if sel.any():
            median = np.median(perf[sel])
            print(f"  edad {lo}-{hi} d: n={sel.sum()} mediana views/día={median:,.0f}")
    print(f"autores distintos: {len({p.url.split('/@')[-1].split('/')[0] for p in tiktok})}")


async def main(as_of: datetime) -> None:
    async with SessionLocal() as session:
        await session.execute(text("SET TRANSACTION READ ONLY"))
        loaded = await load_pieces(session, as_of)
        answers = await load_judgments(session, loaded)
        await session.rollback()
    judgments = {i: to_piece_judgment(i, a) for i, a in answers.items()}
    kept = keep_about_ai(loaded, judgments)
    print(f"as_of={as_of.isoformat()}")
    print(Counter(p.platform.value for p in loaded), "cargadas")
    print(Counter(p.platform.value for p in kept), "tras keep_about_ai")
    _tiktok_age(kept, as_of)
    modes = [("main: referencia = tras Jev", kept), ("#48: referencia = cargadas", loaded)]
    for label, reference in modes:
        _groups(kept, reference, as_of, label)
        _rates(kept, reference, as_of, label)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=datetime.fromisoformat, default=datetime.now(UTC))
    asyncio.run(main(parser.parse_args().as_of))
