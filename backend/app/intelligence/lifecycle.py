"""Etapa de la tendencia (CLAUDE.md §7). Primera regla que se cumple; `unknown` va primero."""

from dataclasses import dataclass

from app.schemas.opportunity import Lifecycle

MIN_ITEMS = 5
SATURATED_MIN = 75
PEAKING_MIN = 60
PEAKING_MAX_ABS_ACCEL = 0.2
ACCELERATING_MIN_ACCEL = 0.5
ACCELERATING_MIN_SOURCES = 3
EMERGING_MAX_SOURCES = 3
EMERGING_MAX_SATURATION = 40


@dataclass(frozen=True)
class Stage:
    lifecycle: Lifecycle
    reason: str


def classify(
    *, acceleration: float, saturation: float, source_count: int, item_count: int
) -> Stage:
    if item_count < MIN_ITEMS or source_count < 2:
        return Stage(
            Lifecycle.UNKNOWN,
            f"Datos insuficientes: {item_count} piezas de {source_count} "
            "fuente(s) independiente(s).",
        )
    if saturation >= SATURATED_MIN and acceleration < 0:
        return Stage(
            Lifecycle.SATURATED,
            f"Saturación {saturation:.0f} ≥ {SATURATED_MIN} y aceleración {acceleration:+.2f} < 0.",
        )
    if saturation >= PEAKING_MIN and abs(acceleration) < PEAKING_MAX_ABS_ACCEL:
        return Stage(
            Lifecycle.PEAKING,
            f"Saturación {saturation:.0f} ≥ {PEAKING_MIN} y |aceleración| "
            f"{abs(acceleration):.2f} < {PEAKING_MAX_ABS_ACCEL}.",
        )
    if acceleration >= ACCELERATING_MIN_ACCEL and source_count >= ACCELERATING_MIN_SOURCES:
        return Stage(
            Lifecycle.ACCELERATING,
            f"Aceleración {acceleration:+.2f} ≥ {ACCELERATING_MIN_ACCEL} y {source_count} "
            f"fuentes independientes (≥ {ACCELERATING_MIN_SOURCES}).",
        )
    if (
        acceleration > 0
        and source_count <= EMERGING_MAX_SOURCES
        and saturation < EMERGING_MAX_SATURATION
    ):
        return Stage(
            Lifecycle.EMERGING,
            f"Aceleración {acceleration:+.2f} > 0, {source_count} fuentes independientes "
            f"(≤ {EMERGING_MAX_SOURCES}) y saturación {saturation:.0f} "
            f"< {EMERGING_MAX_SATURATION}.",
        )
    return Stage(
        Lifecycle.UNKNOWN,
        f"Ninguna regla se cumple (aceleración {acceleration:+.2f}, saturación {saturation:.0f}, "
        f"{source_count} fuentes).",
    )
