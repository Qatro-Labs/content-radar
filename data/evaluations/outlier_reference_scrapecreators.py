"""Tasa de outliers de TikTok, Instagram y Reddit con distintas referencias (mediana, p75, p90).

Solo lee la DB (transacción READ ONLY): no llama a ninguna API ni escribe nada. Usa las mismas
funciones que `analyze` (`load_pieces`, `keep_about_ai`, `outlier_ratios`); para probar otro
cuantil sustituye `outliers.MEDIAN`, que `outlier_ratios` lee en cada llamada para las
plataformas que no son HN.

Hipótesis (no es lo que calcula `analyze`): la misma cuenta sin `MIN_REFERENCE_AGE`. Se hace
pasando a `outlier_ratios` un `as_of` lejano: solo lo usa para la edad mínima de la referencia;
las views/día salen de `observed_at` de cada pieza. `MIN_REFERENCE` sigue aplicándose.

Desde backend/:
    PYTHONPATH=. uv run python ../data/evaluations/outlier_reference_scrapecreators.py \
        --as-of 2026-10-17T21:45:00+00:00
"""

import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

import numpy as np
from sqlalchemy import text

from app.db.session import SessionLocal
from app.intelligence import outliers as out
from app.intelligence.jev import keep_about_ai, to_piece_judgment
from app.intelligence.opportunities import (
    Piece,
    _old_enough_for_reference,
    _performance,
    outlier_ratios,
)
from app.schemas.signal import Platform
from app.services.classification import load_judgments
from app.services.opportunities import load_pieces

PLATFORMS = [Platform.TIKTOK, Platform.INSTAGRAM, Platform.REDDIT, Platform.HACKERNEWS]
QUANTILES = {"mediana": 0.5, "p75": 0.75, "p90": 0.9}
TOP_TITLES = 8
NO_AGE_GATE = timedelta(days=3650)


def _ratios_with(pieces: list[Piece], as_of: datetime, quantile: float) -> dict[int, float | None]:
    original = out.MEDIAN
    out.MEDIAN = quantile
    try:
        return outlier_ratios(pieces, as_of)
    finally:
        out.MEDIAN = original


def _groups(pieces: list[Piece], as_of: datetime) -> None:
    print("\n## Referencias (fuente = perfil, búsqueda o subreddit)")
    by_source: dict[tuple[str, str], list[Piece]] = defaultdict(list)
    for p in pieces:
        if p.platform in PLATFORMS[:3]:
            by_source[(p.platform.value, p.source_name)].append(p)
    for (platform, name), group in sorted(by_source.items()):
        values = [v for p in group if (v := _performance(p)) is not None]
        ref = [
            v
            for p in group
            if (v := _performance(p)) is not None and _old_enough_for_reference(p, as_of)
        ]
        stats = ""
        if ref:
            q = np.quantile(ref, [0.5, 0.75, 0.9])
            stats = (
                f" mediana={q[0]:.1f} p75={q[1]:.1f} p90={q[2]:.1f} max={max(ref):.1f}"
                f" max/mediana={max(ref) / q[0]:.1f}"
                if q[0] > 0
                else ""
            )
        print(
            f"- {platform} · {name}: piezas={len(group)} con métrica={len(values)}"
            f" en referencia={len(ref)}{stats}"
        )


def _share(count: int, total: int) -> str:
    return f"{count} ({count / total:.0%})" if total else "—"


def _rates(pieces: list[Piece], as_of: datetime, label: str) -> None:
    print(f"\n## Tasas ({label}), as_of={as_of.isoformat()}")
    print("| plataforma | referencia | n con métrica | sin referencia | ≥2× | ≥3× |")
    print("|---|---|---|---|---|---|")
    flagged: dict[tuple[str, str], list[tuple[float, Piece]]] = {}
    for qname, q in QUANTILES.items():
        ratios = _ratios_with(pieces, as_of, q)
        for platform in PLATFORMS:
            if platform is Platform.HACKERNEWS and qname != "mediana":
                continue  # HN usa siempre su p90: se muestra una vez como comparación
            group = [p for p in pieces if p.platform is platform and _performance(p) is not None]
            rs = [ratios[p.item_id] for p in group]
            with_ref = [r for r in rs if r is not None]
            notable = sum(r >= out.NOTABLE_RATIO for r in with_ref)
            outlier = sum(r >= out.OUTLIER_RATIO for r in with_ref)
            ref_name = "p90 (actual)" if platform is Platform.HACKERNEWS else qname
            print(
                f"| {platform.value} | {ref_name} | {len(group)} | {len(rs) - len(with_ref)}"
                f" | {_share(notable, len(with_ref))} | {_share(outlier, len(with_ref))} |"
            )
            flagged[(platform.value, qname)] = sorted(
                (
                    (r, p)
                    for p, r in zip(group, rs, strict=True)
                    if r is not None and r >= out.NOTABLE_RATIO
                ),
                key=lambda pair: -pair[0],
            )
    print("\n## Piezas ≥2× por opción (las ≥3× son outliers)")
    for (platform, qname), items in flagged.items():
        if platform == Platform.HACKERNEWS.value:
            continue
        print(f"\n### {platform} · {qname}: {len(items)}")
        for r, p in items[:TOP_TITLES]:
            print(f"- {r:.1f}× · {p.source_name} · {p.title[:90]!r}")


async def main(as_of: datetime) -> None:
    async with SessionLocal() as session:
        await session.execute(text("SET TRANSACTION READ ONLY"))
        loaded = await load_pieces(session, as_of)
        answers = await load_judgments(session, loaded)
        await session.rollback()
    judgments = {i: to_piece_judgment(i, a) for i, a in answers.items()}
    kept = keep_about_ai(loaded, judgments)
    print(Counter(p.platform.value for p in loaded), "cargadas")
    print(Counter(p.platform.value for p in kept), "tras keep_about_ai (lo que ve analyze)")
    _groups(kept, as_of)
    _rates(kept, as_of, "tras keep_about_ai, como analyze")
    _rates(loaded, as_of, "todas las cargadas")
    _rates(kept, as_of + NO_AGE_GATE, "HIPÓTESIS sin MIN_REFERENCE_AGE, tras keep_about_ai")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=datetime.fromisoformat, default=datetime.now(UTC))
    asyncio.run(main(parser.parse_args().as_of))
