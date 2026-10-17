"""Bucle del agente del Radar (plan data-radar-agent, "Bucle" y D2, D4, D5, D10, D13, D14)."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import anthropic
from anthropic.types import MessageParam, ToolResultBlockParam
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.limits import MAX_STEPS
from app.agent.model import AgentModel, ModelTurn, ToolCall
from app.agent.sanitize import (
    ANSWER_MAX_CHARS,
    UNKNOWN_MAX_CHARS,
    UNKNOWNS_MAX,
    clean_output,
    leaks_canary,
    strip_invisible,
    wrap_question,
)
from app.agent.tools import (
    DECLINE,
    FINAL_ANSWER,
    NO_DATA_MESSAGE,
    DeclineInput,
    DeclineReason,
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
TIMEOUT_MESSAGE = "El asistente tardó demasiado. Prueba con una pregunta más concreta."
STEP_LIMIT_MESSAGE = "Límite de pasos alcanzado: responde ya con final_answer."
QUESTION_TIMEOUT_SECONDS = 45
# Texto fijo escrito en código (D10): el modelo solo elige el motivo, nunca redacta el rechazo.
DECLINE_TEXTS = {
    DeclineReason.OFF_TOPIC: (
        "Solo puedo responder sobre las oportunidades editoriales de IA del Radar: temas, etapas, "
        "evidencia y encaje con la audiencia de 30X."
    ),
    DeclineReason.UNSAFE: "No puedo ayudar con esa petición.",
}
DECLINE_UNKNOWNS = ["Esta pregunta queda fuera de lo que mide el Radar."]


class AgentFailedError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.event = ErrorEvent(code=code, message=message)


@dataclass
class RunState:
    deadline: float  # en el reloj del event loop
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


def declined_answer(reason: DeclineReason) -> AnswerEvent:
    return AnswerEvent(text=DECLINE_TEXTS[reason], cited=[], unknowns=list(DECLINE_UNKNOWNS))


def validated_answer(raw: FinalAnswerInput, seen: Seen) -> AnswerEvent:
    text = clean_output(raw.text, seen.evidence_urls, ANSWER_MAX_CHARS)
    unknowns = [clean_output(u, seen.evidence_urls, UNKNOWN_MAX_CHARS) for u in raw.unknowns]
    # Sobre lo limpio, porque limpiar puede volver a juntar un canario partido con una etiqueta o
    # un enlace vacíos; y sobre el original sin invisibles, por si el corte lo deja fuera.
    raw_visible = [strip_invisible(t) for t in (raw.text, *raw.unknowns)]
    if leaks_canary(text, *unknowns, *raw_visible):
        return declined_answer(DeclineReason.UNSAFE)
    cited_ids = dict.fromkeys(i for i in raw.cited_ids if i in seen.opportunities)
    unknowns = [u for u in unknowns if u][:UNKNOWNS_MAX] or [DEFAULT_UNKNOWN]
    return AnswerEvent(
        text=text, cited=[seen.opportunities[i] for i in cited_ids], unknowns=unknowns
    )


def _decline(call: ToolCall) -> AnswerEvent:
    try:
        reason = DeclineInput.model_validate(call.input).reason
    except ValidationError:
        # Si el modelo quiso rechazar pero no dijo por qué bien, se rechaza por lo seguro.
        reason = DeclineReason.UNSAFE
    return declined_answer(reason)


def _final_answer(call: ToolCall, seen: Seen) -> AnswerEvent:
    try:
        raw = FinalAnswerInput.model_validate(call.input)
    except ValidationError as e:
        raise AgentFailedError(ErrorCode.INTERNAL, INTERNAL_MESSAGE) from e
    return validated_answer(raw, seen)


def _closing_answer(turn: ModelTurn, state: RunState) -> AnswerEvent | None:
    by_name = {c.name: c for c in turn.tool_calls}
    if DECLINE in by_name:
        return _decline(by_name[DECLINE])
    if FINAL_ANSWER in by_name:
        return _final_answer(by_name[FINAL_ANSWER], state.seen)
    return None


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


def _nudge_once(*, already_nudged: bool) -> bool:
    # Texto suelto sin tools: se descarta y se pide la respuesta final una sola vez.
    if already_nudged:
        raise AgentFailedError(ErrorCode.INTERNAL, INTERNAL_MESSAGE)
    return True


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
        async with asyncio.timeout_at(state.deadline):
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
        # Sin `yield` dentro del timeout: la cancelación nunca cae fuera de este bucle.
        async with asyncio.timeout_at(state.deadline):
            turn = await model.next_turn(messages, force_final=force_final)
        meter.add(
            Provider.LLM_TEXT, AGENT_OPERATION, turn.input_tokens, output_units=turn.output_tokens
        )
        answer = _closing_answer(turn, state)
        if answer is not None:
            yield answer
            return
        if not turn.tool_calls:
            nudged = _nudge_once(already_nudged=nudged)
            continue
        results: list[ToolResultBlockParam] = []
        async for event in _run_tools(turn, state, session, results):
            yield event
        messages.append({"role": "assistant", "content": turn.content_blocks})
        messages.append({"role": "user", "content": results})


async def run_agent(
    question: str, *, model: AgentModel, session: AsyncSession, meter: UsageMeter
) -> AsyncIterator[AgentEvent]:
    state = RunState(deadline=asyncio.get_running_loop().time() + QUESTION_TIMEOUT_SECONDS)
    if await opportunities.list_opportunities(session) is None:
        yield ErrorEvent(code=ErrorCode.NO_DATA, message=NO_DATA_MESSAGE)
        yield state.done()
        return
    messages: list[MessageParam] = [{"role": "user", "content": wrap_question(question)}]
    try:
        async for event in _loop(messages, model=model, state=state, session=session, meter=meter):
            yield event
    except anthropic.APIError:
        yield ErrorEvent(code=ErrorCode.LLM_UNAVAILABLE, message=LLM_UNAVAILABLE_MESSAGE)
    except TimeoutError:
        yield ErrorEvent(code=ErrorCode.TIMEOUT, message=TIMEOUT_MESSAGE)
    except SQLAlchemyError:
        # Sin el texto de la excepción (D15): puede llevar SQL o nombres internos.
        yield ErrorEvent(code=ErrorCode.INTERNAL, message=INTERNAL_MESSAGE)
    except AgentFailedError as e:
        yield e.event
    yield state.done()
