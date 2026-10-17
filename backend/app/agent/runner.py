"""Bucle del agente del Radar (plan data-radar-agent, "Bucle" y D2, D4, D5)."""

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import anthropic
from anthropic.types import MessageParam, ToolResultBlockParam
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.limits import MAX_STEPS
from app.agent.model import AgentModel, ModelTurn, ToolCall
from app.agent.tools import (
    FINAL_ANSWER,
    NO_DATA_MESSAGE,
    FinalAnswerInput,
    Seen,
    ToolOutcome,
    execute_tool,
    pending_step,
)
from app.collectors.usage import UsageMeter
from app.schemas.agent import (
    ActionEvent,
    AgentEvent,
    AnswerEvent,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    StepEvent,
    StepKind,
    StepStatus,
)
from app.schemas.cost import Provider
from app.services import opportunities

AGENT_OPERATION = "agent"
DEFAULT_UNKNOWN = "El agente no indicó límites: revisa la evidencia de cada oportunidad citada."
LLM_UNAVAILABLE_MESSAGE = "El asistente no está disponible ahora mismo."
INTERNAL_MESSAGE = "El asistente no pudo terminar la respuesta."
STEP_LIMIT_MESSAGE = "Límite de pasos alcanzado: responde ya con final_answer."
URL_PATTERN = re.compile(r"https?://\S+")
# Puntuación que suele pegarse al final de una URL en una frase y no forma parte de ella.
URL_TRAILING_PUNCTUATION = ".,;:!?)»\"'"


class AgentFailedError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.event = ErrorEvent(code=code, message=message)


@dataclass
class RunState:
    seen: Seen = field(default_factory=Seen)
    data_steps: int = 0
    view_steps: int = 0

    @property
    def steps(self) -> int:
        return self.data_steps + self.view_steps

    def count(self, kind: StepKind) -> int:
        if kind is StepKind.DATA:
            self.data_steps += 1
        else:
            self.view_steps += 1
        return self.steps

    def done(self) -> DoneEvent:
        return DoneEvent(steps=self.steps, data_steps=self.data_steps, view_steps=self.view_steps)


def _keep_seen_url(match: re.Match[str], seen_urls: set[str]) -> str:
    url = match.group(0).rstrip(URL_TRAILING_PUNCTUATION)
    trailing = match.group(0)[len(url) :]
    return match.group(0) if url in seen_urls else trailing


def validated_answer(raw: FinalAnswerInput, seen: Seen) -> AnswerEvent:
    cited_ids = dict.fromkeys(i for i in raw.cited_ids if i in seen.opportunities)
    text = URL_PATTERN.sub(lambda m: _keep_seen_url(m, seen.evidence_urls), raw.text)
    unknowns = [u for u in raw.unknowns if u.strip()] or [DEFAULT_UNKNOWN]
    return AnswerEvent(
        text=text, cited=[seen.opportunities[i] for i in cited_ids], unknowns=unknowns
    )


def _final_answer(turn: ModelTurn, state: RunState) -> AnswerEvent | None:
    call = next((c for c in turn.tool_calls if c.name == FINAL_ANSWER), None)
    if call is None:
        return None
    try:
        raw = FinalAnswerInput.model_validate(call.input)
    except ValidationError as e:
        raise AgentFailedError(ErrorCode.INTERNAL, INTERNAL_MESSAGE) from e
    return validated_answer(raw, state.seen)


def _tool_result(call: ToolCall, content: str, *, is_error: bool) -> ToolResultBlockParam:
    return {"type": "tool_result", "tool_use_id": call.id, "content": content, "is_error": is_error}


def _step_events(step_id: int, outcome: ToolOutcome) -> list[AgentEvent]:
    status = StepStatus.FAILED if outcome.is_error else StepStatus.DONE
    events: list[AgentEvent] = [
        StepEvent(id=step_id, kind=outcome.kind, label=outcome.label, status=status)
    ]
    if outcome.patch is not None and not outcome.is_error:
        events.append(ActionEvent(step_id=step_id, patch=outcome.patch))
    return events


async def _run_tools(
    turn: ModelTurn, state: RunState, session: AsyncSession, results: list[ToolResultBlockParam]
) -> AsyncIterator[AgentEvent]:
    for call in turn.tool_calls:
        if state.steps >= MAX_STEPS:
            results.append(_tool_result(call, STEP_LIMIT_MESSAGE, is_error=True))
            continue
        pending = pending_step(call.name)
        step_id = state.count(pending.kind)
        yield StepEvent(
            id=step_id, kind=pending.kind, label=pending.label, status=StepStatus.RUNNING
        )
        outcome = await execute_tool(call.name, call.input, session, state.seen)
        results.append(_tool_result(call, outcome.content, is_error=outcome.is_error))
        for event in _step_events(step_id, outcome):
            yield event


async def _loop(
    messages: list[MessageParam],
    *,
    model: AgentModel,
    state: RunState,
    session: AsyncSession,
    meter: UsageMeter,
) -> AsyncIterator[AgentEvent]:
    nudged = False
    while True:
        force_final = nudged or state.steps >= MAX_STEPS
        turn = await model.next_turn(messages, force_final=force_final)
        meter.add(
            Provider.LLM_TEXT, AGENT_OPERATION, turn.input_tokens, output_units=turn.output_tokens
        )
        answer = _final_answer(turn, state)
        if answer is not None:
            yield answer
            return
        if not turn.tool_calls:
            # Texto suelto sin tools: se descarta y se pide la respuesta final una sola vez.
            if nudged:
                raise AgentFailedError(ErrorCode.INTERNAL, INTERNAL_MESSAGE)
            nudged = True
            continue
        results: list[ToolResultBlockParam] = []
        async for event in _run_tools(turn, state, session, results):
            yield event
        messages.append({"role": "assistant", "content": turn.content_blocks})
        messages.append({"role": "user", "content": results})


async def run_agent(
    question: str, *, model: AgentModel, session: AsyncSession, meter: UsageMeter
) -> AsyncIterator[AgentEvent]:
    state = RunState()
    if await opportunities.list_opportunities(session) is None:
        yield ErrorEvent(code=ErrorCode.NO_DATA, message=NO_DATA_MESSAGE)
        yield state.done()
        return
    messages: list[MessageParam] = [{"role": "user", "content": question}]
    try:
        async for event in _loop(messages, model=model, state=state, session=session, meter=meter):
            yield event
    except anthropic.APIError:
        yield ErrorEvent(code=ErrorCode.LLM_UNAVAILABLE, message=LLM_UNAVAILABLE_MESSAGE)
    except AgentFailedError as e:
        yield e.event
    yield state.done()
