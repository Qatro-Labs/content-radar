"""Caché de las llamadas al LLM en `llm_evaluations`, compartida por todas las operaciones.

Una entrada ya evaluada no se vuelve a enviar mientras no cambie su clave (entrada, prompt y
modelo).
"""

from collections.abc import Mapping, Sequence

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.editorial.evaluator import LlmResult
from app.models import LlmEvaluation


async def load_cached[T: BaseModel](
    session: AsyncSession, keys: Sequence[str], output_type: type[T]
) -> dict[str, T]:
    rows = await session.execute(
        select(LlmEvaluation.cache_key, LlmEvaluation.output).where(
            LlmEvaluation.cache_key.in_(keys)
        )
    )
    return {key: output_type.model_validate(output) for key, output in rows.all()}


async def save_results(
    session: AsyncSession,
    evaluated: Mapping[str, LlmResult],
    *,
    operation: str,
    prompt_version: int,
    opportunity_ids: Mapping[str, str],
) -> None:
    if not evaluated:
        return
    rows = [
        {
            "cache_key": key,
            "operation": operation,
            "prompt_version": prompt_version,
            "requested_model": get_settings().llm_model,
            "response_model": result.model,
            "opportunity_id": opportunity_ids[key],
            "output": result.output.model_dump(mode="json"),
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }
        for key, result in evaluated.items()
    ]
    stmt = insert(LlmEvaluation).values(rows).on_conflict_do_nothing(index_elements=["cache_key"])
    await session.execute(stmt)
    # Commit en cuanto llegan: si el job falla después, las llamadas ya pagadas no se pierden.
    await session.commit()
