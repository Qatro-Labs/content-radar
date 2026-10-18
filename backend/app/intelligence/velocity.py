"""Velocidad y aceleración: de un tema (por `published_at`) y de una pieza (entre snapshots).

La aceleración del tema se mide sobre su **cuota del corpus**, no sobre el conteo bruto: los
feeds RSS solo guardan sus últimas N piezas, así que los días recientes tienen más volumen en
todas partes. Sin corregirlo, casi todos los temas parecerían acelerar.

Con pocas piezas, una subida grande puede ser azar: pasar de 1 a 2 ya es +100 %. Por eso la
aceleración lleva un p-valor (`acceleration_p_value`) y el momentum usa un log-ratio suavizado
(`TopicVelocity.log_ratio`) en vez del cambio relativo.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

WINDOW = timedelta(days=3)
# Una pieza de pseudo-conteo en cada ventana: 2 frente a 1 no pesa como 70 frente a 5.
RATE_PSEUDO_COUNT = 1.0


@dataclass(frozen=True)
class WindowCounts:
    current: int
    previous: int


@dataclass(frozen=True)
class TopicVelocity:
    velocity: float  # piezas/día en la ventana actual
    acceleration: float  # cambio relativo vs. la ventana anterior, ajustado por volumen
    log_ratio: float  # log2 de la razón de tasas suavizada; lo usa el momentum
    current_count: int
    previous_count: int


def window_counts(
    published: Sequence[datetime], as_of: datetime, window: timedelta = WINDOW
) -> WindowCounts:
    """Piezas en (as_of − window, as_of] y en (as_of − 2·window, as_of − window]."""
    current = previous = 0
    for p in published:
        age = as_of - p
        if timedelta(0) <= age < window:
            current += 1
        elif window <= age < 2 * window:
            previous += 1
    return WindowCounts(current, previous)


def topic_velocity(
    topic: WindowCounts, corpus: WindowCounts, window: timedelta = WINDOW
) -> TopicVelocity:
    """`velocity` en piezas/día. `acceleration = (v − v_prev_aj) / max(v_prev_aj, 1)` en conteos,
    donde `v_prev_aj` es la ventana anterior escalada al volumen del corpus en la actual.
    """
    days = window / timedelta(days=1)
    expected = _expected_current(topic, corpus)
    acceleration = (topic.current - expected) / max(expected, 1.0)
    log_ratio = math.log2((topic.current + RATE_PSEUDO_COUNT) / (expected + RATE_PSEUDO_COUNT))
    return TopicVelocity(
        velocity=round(topic.current / days, 2),
        acceleration=round(acceleration, 2),
        log_ratio=round(log_ratio, 3),
        current_count=topic.current,
        previous_count=topic.previous,
    )


def _expected_current(topic: WindowCounts, corpus: WindowCounts) -> float:
    """La ventana anterior del tema, escalada al volumen del corpus en la actual."""
    scale = corpus.current / corpus.previous if corpus.previous else 1.0
    return topic.previous * scale


def acceleration_p_value(topic: WindowCounts, corpus: WindowCounts) -> float:
    """Probabilidad de ver al menos `topic.current` piezas en la ventana actual si el tema
    creciera al mismo ritmo que el corpus. Test exacto de razón de tasas de Poisson: condicionado
    a `current + previous`, el conteo actual es binomial con p0 = la cuota del corpus en la
    ventana actual. 1.0 cuando no se puede medir (sin piezas o sin corpus en alguna ventana).
    """
    n = topic.current + topic.previous
    if n == 0 or corpus.current == 0 or corpus.previous == 0:
        return 1.0
    p0 = corpus.current / (corpus.current + corpus.previous)
    tail = sum(math.comb(n, k) * p0**k * (1 - p0) ** (n - k) for k in range(topic.current, n + 1))
    return round(min(tail, 1.0), 3)


def piece_rate(snapshots: Sequence[tuple[datetime, int | None]]) -> float | None:
    """Δmétrica / Δhoras entre el primer y el último snapshot con valor. None sin 2 mediciones."""
    points = sorted((t, v) for t, v in snapshots if v is not None)
    if len(points) < 2:
        return None
    (t0, v0), (t1, v1) = points[0], points[-1]
    hours = (t1 - t0) / timedelta(hours=1)
    if hours <= 0:
        return None
    return round((v1 - v0) / hours, 2)
