"""«Por qué importa» del LLM, comprobado en Python antes de publicarse (CLAUDE.md §2, regla 3).

Aquí no hay LLM ni DB: entran las afirmaciones tal cual y salen solo las que citan una pieza que
el LLM recibió y no traen cifras que no estén en los datos o en la evidencia. Con la verificación
de Jev activa, el texto se compone en una segunda etapa solo con lo que Jev respaldó y sus notas.
"""

import re
from collections.abc import Sequence, Set
from dataclasses import dataclass, replace

from app.intelligence.audience_fit import EDITORIAL_PENDING_NOTE
from app.intelligence.opportunities import TopicResult

# "1.000", "1,000", "2,5" y "2.5" se comparan solo por sus dígitos.
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
MAX_LIMITATIONS = 2
MAX_LIMITATION_CHARS = 240

EXPLANATION_FAILED_NOTE = "No se pudo redactar «por qué importa»: se muestran los datos medidos."
NO_VALID_CLAIM_NOTE = (
    "Ninguna afirmación del LLM superó la comprobación de evidencia: se muestran los datos medidos."
)
VERIFICATION_INCOMPLETE_NOTE = (
    "No se pudo completar la verificación de «por qué importa» con Jev: se muestran los datos "
    "medidos."
)


@dataclass(frozen=True)
class ClaimDraft:
    text: str
    cited_urls: list[str]


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[.,]", "", m) for m in NUMBER.findall(text)}


def numbers_supported(text: str, known_numbers: Set[str]) -> bool:
    return _numbers(text) <= known_numbers


def known_numbers(texts: Sequence[str]) -> set[str]:
    return set().union(*(_numbers(t) for t in texts))


def _with_notes(result: TopicResult, why: str | None, notes: list[str]) -> TopicResult:
    o = result.opportunity
    kept = [n for n in o.limitations if n != EDITORIAL_PENDING_NOTE]
    update: dict[str, object] = {"limitations": kept + notes}
    if why is not None:
        update["why_it_matters"] = why
    return replace(result, opportunity=o.model_copy(update=update))


def python_checked(
    claims: Sequence[ClaimDraft], *, sent_urls: Set[str], numbers: Set[str]
) -> list[ClaimDraft]:
    return [
        c
        for c in claims
        if any(u in sent_urls for u in c.cited_urls) and numbers_supported(c.text, numbers)
    ]


def _claims_count(n: int) -> str:
    return "1 afirmación" if n == 1 else f"{n} afirmaciones"


def python_drop_note(dropped: int) -> str | None:
    if not dropped:
        return None
    return (
        f"Se descartaron {_claims_count(dropped)} del LLM sin evidencia o con cifras no observadas."
    )


def jev_drop_note(dropped: int) -> str | None:
    if not dropped:
        return None
    verb = "no se publica" if dropped == 1 else "no se publican"
    return (
        f"Jev no encontró respaldo en la evidencia citada para {_claims_count(dropped)} del LLM: "
        f"{verb}."
    )


def jev_unverified_note(unverified: int) -> str | None:
    if not unverified:
        return None
    verb = "no se publica" if unverified == 1 else "no se publican"
    return f"Jev no pudo verificar {_claims_count(unverified)} del LLM: {verb}."


def compose_explanation(
    result: TopicResult,
    published: Sequence[ClaimDraft],
    limitations: Sequence[str],
    *,
    numbers: Set[str],
    notes: Sequence[str | None],
) -> TopicResult:
    if not published:
        return _with_notes(result, None, [NO_VALID_CLAIM_NOTE])
    kept = [
        " ".join(n.split())
        for n in limitations[:MAX_LIMITATIONS]
        if n.strip() and len(n) <= MAX_LIMITATION_CHARS and numbers_supported(n, numbers)
    ]
    why = " ".join(" ".join(c.text.split()) for c in published)
    return _with_notes(result, why, kept + [n for n in notes if n is not None])


def apply_explanation(
    result: TopicResult,
    claims: Sequence[ClaimDraft],
    limitations: Sequence[str],
    *,
    sent_urls: Set[str],
    numbers: Set[str],
) -> TopicResult:
    valid = python_checked(claims, sent_urls=sent_urls, numbers=numbers)
    notes = [python_drop_note(len(claims) - len(valid))]
    return compose_explanation(result, valid, limitations, numbers=numbers, notes=notes)


def mark_explanation_failed(result: TopicResult) -> TopicResult:
    return _with_notes(result, None, [EXPLANATION_FAILED_NOTE])


def mark_verification_incomplete(result: TopicResult) -> TopicResult:
    return _with_notes(result, None, [VERIFICATION_INCOMPLETE_NOTE])
