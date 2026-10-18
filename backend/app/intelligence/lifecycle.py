"""Etapa de la tendencia (CLAUDE.md §7). Primera regla que se cumple; `unknown` va primero.

`accelerating` afirma un crecimiento sostenido, así que además exige que la subida no se explique
por azar (`acceleration_p_value` ≤ `ACCELERATION_MAX_P`). `emerging` es temprano por definición:
no lleva esa puerta, pero su razón avisa cuando la subida aún puede ser azar.
"""

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
# Por tema, sin corregir por comparaciones múltiples: con ventanas de 3 días y pocas piezas,
# Benjamini–Hochberg sobre todos los temas no deja pasar ninguno. Se documenta como limitación.
ACCELERATION_MAX_P = 0.10


@dataclass(frozen=True)
class Stage:
    lifecycle: Lifecycle
    reason: str
    # unknown por falta de datos (no por no cumplir ninguna regla)
    insufficient: bool = False


def is_insufficient(source_count: int, item_count: int) -> bool:
    return item_count < MIN_ITEMS or source_count < 2


def classify(
    *,
    acceleration: float,
    p_value: float,
    saturation: float,
    source_count: int,
    item_count: int,
) -> Stage:
    if is_insufficient(source_count, item_count):
        return Stage(
            Lifecycle.UNKNOWN,
            f"Datos insuficientes: {item_count} piezas de {source_count} "
            "fuente(s) independiente(s).",
            insufficient=True,
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
    accelerating = (
        acceleration >= ACCELERATING_MIN_ACCEL and source_count >= ACCELERATING_MIN_SOURCES
    )
    if accelerating and p_value <= ACCELERATION_MAX_P:
        return Stage(
            Lifecycle.ACCELERATING,
            f"Aceleración {acceleration:+.2f} ≥ {ACCELERATING_MIN_ACCEL} (p = {p_value:.2f}) y "
            f"{source_count} fuentes independientes (≥ {ACCELERATING_MIN_SOURCES}).",
        )
    if (
        acceleration > 0
        and source_count <= EMERGING_MAX_SOURCES
        and saturation < EMERGING_MAX_SATURATION
    ):
        return Stage(
            Lifecycle.EMERGING,
            f"Aceleración {acceleration:+.2f} > 0 (p = {p_value:.2f}), {source_count} fuentes "
            f"independientes (≤ {EMERGING_MAX_SOURCES}) y saturación {saturation:.0f} "
            f"< {EMERGING_MAX_SATURATION}.{_unproven_note(p_value)}",
        )
    if accelerating:
        return Stage(
            Lifecycle.UNKNOWN,
            f"Aceleración {acceleration:+.2f} sin demostrar: p = {p_value:.2f} > "
            f"{ACCELERATION_MAX_P}, con tan pocas piezas la subida puede ser azar.",
        )
    if acceleration < 0:
        # Sin etapa `declining` en el contrato: el texto explica que el tema se enfría.
        return Stage(
            Lifecycle.UNKNOWN,
            f"En descenso: aceleración {acceleration:+.0%}, saturación {saturation:.0f}, "
            f"{source_count} fuentes. Ninguna etapa aplica.",
        )
    return Stage(
        Lifecycle.UNKNOWN,
        f"Ninguna regla se cumple (aceleración {acceleration:+.2f}, saturación {saturation:.0f}, "
        f"{source_count} fuentes).",
    )


def _unproven_note(p_value: float) -> str:
    if p_value <= ACCELERATION_MAX_P:
        return ""
    return " Señal temprana: con tan pocas piezas, la subida aún puede ser azar."
