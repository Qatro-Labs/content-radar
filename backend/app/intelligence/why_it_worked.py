"""«Por qué funcionó», medido: ganchos de los outliers frente al resto del tema (CLAUDE.md §7).

lift = (% de outliers con el gancho) / (% del resto con el gancho). Un gancho con lift ≥ 2 que
usan al menos 2 outliers es un patrón observado; si no, es anecdótico. Es una hipótesis con
muestra pequeña, nunca causalidad. El gancho lo decide Jev (`hook` y `hook_rev` de acuerdo).
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import replace

from app.intelligence import outliers as out
from app.intelligence.opportunities import TopicResult
from app.schemas.opportunity import HookLift, OutlierHooks

MIN_PATTERN_OUTLIERS = 2
MIN_PATTERN_LIFT = 2.0
MIN_REST = 2  # con menos piezas normales no hay con qué comparar


def outlier_hooks(
    samples: Sequence[tuple[float | None, str | None]],
) -> OutlierHooks | None:
    """`samples`: (outlier_ratio, gancho) de cada pieza original del tema."""
    # Sin ratio no se sabe si la pieza es outlier: no entra ni en un lado ni en el otro.
    rated = [(ratio, hook) for ratio, hook in samples if ratio is not None]
    outlier_labels = [hook for ratio, hook in rated if ratio >= out.OUTLIER_RATIO]
    outliers = Counter(h for h in outlier_labels if h is not None)
    rest = Counter(h for ratio, h in rated if ratio < out.OUTLIER_RATIO and h is not None)
    if not outliers:
        return None
    outliers_total, rest_total = outliers.total(), rest.total()
    hooks = [
        _lift(
            hook,
            o_with=outliers[hook],
            o_total=outliers_total,
            r_with=rest[hook],
            r_total=rest_total,
        )
        for hook in sorted(outliers, key=lambda h: (-outliers[h], h))
    ]
    return OutlierHooks(hooks=hooks, outliers_unclassified=len(outlier_labels) - outliers_total)


def _lift(hook: str, *, o_with: int, o_total: int, r_with: int, r_total: int) -> HookLift:
    lift = (o_with / o_total) / (r_with / r_total) if r_with else None
    pattern = (
        o_with >= MIN_PATTERN_OUTLIERS
        and r_total >= MIN_REST
        and (lift is None or lift >= MIN_PATTERN_LIFT)
    )
    return HookLift(
        hook=hook,
        outliers_with=o_with,
        outliers_total=o_total,
        rest_with=r_with,
        rest_total=r_total,
        lift=round(lift, 2) if lift is not None else None,
        observed_pattern=pattern,
    )


def with_outlier_hooks(
    results: Sequence[TopicResult], hooks: Mapping[int, str | None]
) -> list[TopicResult]:
    # Solo piezas originales: una republicación copia el título, y con él el gancho.
    updated = []
    for r in results:
        samples = [
            (r.ratios.get(p.item_id), hooks.get(p.item_id))
            for p in r.pieces
            if p.item_id not in r.replica_ids
        ]
        opportunity = r.opportunity.model_copy(update={"outlier_hooks": outlier_hooks(samples)})
        updated.append(replace(r, opportunity=opportunity))
    return updated
