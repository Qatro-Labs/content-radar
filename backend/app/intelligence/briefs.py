"""Brief del LLM comprobado en Python antes de publicarse (CLAUDE.md §2, regla 3).

Aquí no hay LLM ni DB. Los datos (`key_points`, `why_it_fits`) tienen que citar una pieza que el
LLM recibió y no traer cifras que no estén en los datos o en la evidencia. Las partes creativas
(ángulo, gancho, estructura) no citan, pero tampoco pueden traer cifras inventadas. Lo que no
pasa se quita con una limitación; sin ángulo o sin ningún dato válido no hay brief.
"""

import html
from collections.abc import Sequence, Set
from dataclasses import dataclass

from app.intelligence.explanation import (
    MAX_LIMITATION_CHARS,
    MAX_LIMITATIONS,
    ClaimDraft,
    numbers_supported,
)

HOOK_DROPPED_NOTE = "Se quitó el gancho propuesto: traía cifras que no están en la evidencia."
FIT_DROPPED_NOTE = "Se quitó «por qué encaja»: no citaba evidencia o traía cifras no observadas."


@dataclass(frozen=True)
class BriefDraftParts:
    angle: str
    hook: str
    structure: Sequence[str]
    key_points: Sequence[ClaimDraft]
    why_it_fits: ClaimDraft
    limitations: Sequence[str]


@dataclass(frozen=True)
class CheckedBrief:
    angle: str
    hook: str | None
    structure: list[str]
    key_points: list[ClaimDraft]  # solo con las URLs enviadas
    why_it_fits: str | None
    limitations: list[str]


def _clean(text: str) -> str:
    return " ".join(text.split())


def _cited(claim: ClaimDraft, sent_urls: Set[str]) -> list[str]:
    # El modelo puede devolver la URL tal como la vio, con el escapado del bloque de evidencia.
    return [u for u in dict.fromkeys(html.unescape(u) for u in claim.cited_urls) if u in sent_urls]


def _valid_claim(claim: ClaimDraft, sent_urls: Set[str], numbers: Set[str]) -> ClaimDraft | None:
    cited = _cited(claim, sent_urls)
    if not cited or not claim.text.strip() or not numbers_supported(claim.text, numbers):
        return None
    return ClaimDraft(_clean(claim.text), cited)


def _dropped_note(count: int, singular: str, plural: str) -> list[str]:
    if count == 0:
        return []
    what = f"se quitó 1 {singular}" if count == 1 else f"se quitaron {count} {plural}"
    return [f"{what.capitalize()} del LLM sin evidencia o con cifras no observadas."]


def check_brief(
    draft: BriefDraftParts, *, sent_urls: Set[str], numbers: Set[str]
) -> CheckedBrief | None:
    """None si no queda ángulo o ningún dato respaldado."""
    points = [p for c in draft.key_points if (p := _valid_claim(c, sent_urls, numbers))]
    if not points or not draft.angle.strip() or not numbers_supported(draft.angle, numbers):
        return None
    hook = _clean(draft.hook) if numbers_supported(draft.hook, numbers) else None
    steps = [_clean(s) for s in draft.structure if s.strip() and numbers_supported(s, numbers)]
    fit = _valid_claim(draft.why_it_fits, sent_urls, numbers)

    notes = [
        _clean(n)
        for n in draft.limitations[:MAX_LIMITATIONS]
        if n.strip() and len(n) <= MAX_LIMITATION_CHARS and numbers_supported(n, numbers)
    ]
    notes += _dropped_note(len(draft.key_points) - len(points), "dato", "datos")
    notes += _dropped_note(len(draft.structure) - len(steps), "paso", "pasos")
    if hook is None and draft.hook.strip():
        notes.append(HOOK_DROPPED_NOTE)
    if fit is None:
        notes.append(FIT_DROPPED_NOTE)
    return CheckedBrief(
        angle=_clean(draft.angle),
        hook=hook or None,
        structure=steps,
        key_points=points,
        why_it_fits=fit.text if fit else None,
        limitations=notes,
    )
