"""Seam del modelo del agente (plan data-radar-agent, D6): el bucle no conoce el SDK."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from anthropic import AsyncAnthropic
from anthropic.types import ContentBlock, MessageParam, ToolChoiceParam

from app.agent.limits import MAX_OUTPUT_TOKENS
from app.agent.tools import FINAL_ANSWER, TOOL_SCHEMAS
from app.core.config import Settings

PROMPT_VERSION = 1
PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / f"radar_agent.v{PROMPT_VERSION}.md"
TOOL_USE = "tool_use"


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    input: dict[str, object]


@dataclass(frozen=True)
class ModelTurn:
    content_blocks: list[ContentBlock]  # se reenvía tal cual como turno del asistente
    tool_calls: list[ToolCall]
    input_tokens: int
    output_tokens: int


class AgentModel(Protocol):
    async def next_turn(self, messages: list[MessageParam], *, force_final: bool) -> ModelTurn: ...


@lru_cache
def system_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


def _tool_calls(blocks: list[ContentBlock]) -> list[ToolCall]:
    return [
        ToolCall(b.id, b.name, b.input if isinstance(b.input, dict) else {})
        for b in blocks
        if b.type == TOOL_USE
    ]


class AnthropicAgentModel:
    def __init__(self, client: AsyncAnthropic, model: str) -> None:
        self._client = client
        self._model = model

    async def next_turn(self, messages: list[MessageParam], *, force_final: bool) -> ModelTurn:
        tool_choice: ToolChoiceParam = (
            {"type": "tool", "name": FINAL_ANSWER} if force_final else {"type": "auto"}
        )
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=system_prompt(),
            tools=TOOL_SCHEMAS,
            messages=messages,
            tool_choice=tool_choice,
        )
        return ModelTurn(
            content_blocks=response.content,
            tool_calls=_tool_calls(response.content),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


def build_agent_model(settings: Settings) -> AgentModel | None:
    if not settings.llm_api_key or not settings.llm_model:
        return None
    # Reintentos por defecto del SDK (2, con backoff en 408, 429 y 5xx).
    return AnthropicAgentModel(AsyncAnthropic(api_key=settings.llm_api_key), settings.llm_model)
