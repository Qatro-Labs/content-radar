"""`evaluate_topic` con el SDK oficial de Anthropic (CLAUDE.md §7, plan intel-phase1-llm-fit D1)."""

import asyncio
from dataclasses import dataclass
from typing import Protocol

import anthropic
from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.editorial.audience import TopicEvaluation, TopicInput, system_prompt, user_message

# Seis justificaciones de dos o tres frases rondan 1.000–1.500 tokens: margen de sobra para que
# una respuesta larga no se corte.
MAX_OUTPUT_TOKENS = 4096
# Plan intel-phase1-llm-fit, D9.
LLM_CONCURRENCY = 4
# Con salida estructurada, `end_turn` es el único final con un JSON completo: `max_tokens` lo
# corta y `refusal` no lo trae.
COMPLETE_STOP_REASON = "end_turn"


class EvaluationError(Exception):
    """El tema queda sin evaluar. El mensaje nunca lleva texto de la evidencia."""


@dataclass(frozen=True)
class LlmResult[T: BaseModel]:
    model: str
    output: T
    input_tokens: int
    output_tokens: int


EvaluationResult = LlmResult[TopicEvaluation]


class TopicEvaluator(Protocol):
    async def evaluate(self, topic: TopicInput) -> EvaluationResult: ...


# Una llamada con salida estructurada validada con Pydantic: la comparten `evaluate_topic` y
# `explain_opportunity`. `EvaluationError` si la respuesta no llega entera y válida.
class StructuredLlm:
    def __init__(self, client: AsyncAnthropic, model: str, semaphore: asyncio.Semaphore) -> None:
        self._client = client
        self._model = model
        self._semaphore = semaphore

    async def complete[T: BaseModel](
        self, *, system: str, user: str, output_type: type[T]
    ) -> LlmResult[T]:
        schema = anthropic.transform_schema(output_type.model_json_schema())
        try:
            async with self._semaphore:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=MAX_OUTPUT_TOKENS,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    output_config={"format": {"type": "json_schema", "schema": schema}},
                )
        except anthropic.APIError as e:
            raise EvaluationError(type(e).__name__) from e
        # Antes de leer la respuesta: un rechazo o un corte no traen un JSON completo.
        if response.stop_reason != COMPLETE_STOP_REASON:
            raise EvaluationError(f"stop_reason={response.stop_reason}")
        text = "".join(block.text for block in response.content if block.type == "text")
        try:
            output = output_type.model_validate_json(text)
        except ValidationError as e:
            raise EvaluationError("invalid_output") from e
        return LlmResult(
            model=response.model,
            output=output,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


class AnthropicTopicEvaluator:
    def __init__(self, client: AsyncAnthropic, model: str, semaphore: asyncio.Semaphore) -> None:
        self._llm = StructuredLlm(client, model, semaphore)

    async def evaluate(self, topic: TopicInput) -> EvaluationResult:
        return await self._llm.complete(
            system=system_prompt(), user=user_message(topic), output_type=TopicEvaluation
        )


def build_evaluator(settings: Settings) -> TopicEvaluator | None:
    if not settings.llm_api_key or not settings.llm_model:
        return None
    client = AsyncAnthropic(api_key=settings.llm_api_key)
    return AnthropicTopicEvaluator(client, settings.llm_model, asyncio.Semaphore(LLM_CONCURRENCY))
