from collections.abc import AsyncIterable, Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.limits import GLOBAL_PER_DAY, PER_IP_PER_HOUR, LimitResult, RateLimiter
from app.agent.model import AgentModel, build_agent_model
from app.agent.runner import run_agent
from app.collectors.usage import UsageMeter
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.agent import (
    ActionEvent,
    AgentEvent,
    AgentQuestion,
    AnswerEvent,
    DoneEvent,
    ErrorEvent,
    StepEvent,
)
from app.services.costs import record_meter

router = APIRouter(prefix="/agent", tags=["agent"])

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]
NOT_CONFIGURED = "El asistente no está configurado."
LIMIT_MESSAGES = {
    LimitResult.IP: "Has hecho demasiadas preguntas seguidas. Prueba en unos minutos.",
    LimitResult.GLOBAL: "El asistente ha alcanzado el límite de hoy. Prueba mañana.",
}
UNKNOWN_CLIENT = "unknown"
EVENT_NAMES: dict[type, str] = {
    StepEvent: "step",
    ActionEvent: "action",
    AnswerEvent: "answer",
    ErrorEvent: "error",
    DoneEvent: "done",
}

_limiter = RateLimiter(per_ip_per_hour=PER_IP_PER_HOUR, global_per_day=GLOBAL_PER_DAY)


@lru_cache
def get_agent_model() -> AgentModel | None:
    return build_agent_model(get_settings())


def get_rate_limiter() -> RateLimiter:
    return _limiter


def get_session_factory() -> SessionFactory:
    # La vida de una dependencia con `yield` no cubre todo el stream: la sesión la abre el
    # generador (plan data-radar-agent, D7).
    return SessionLocal


def check_agent_allowed(
    request: Request,
    model: Annotated[AgentModel | None, Depends(get_agent_model)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AgentModel:
    if model is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NOT_CONFIGURED)
    # Detrás del proxy de Railway, uvicorn ya pone aquí la IP real (--proxy-headers).
    ip = request.client.host if request.client else UNKNOWN_CLIENT
    result = limiter.check(ip, datetime.now(UTC))
    if result is not LimitResult.OK:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, LIMIT_MESSAGES[result])
    return model


def _to_sse(event: AgentEvent) -> ServerSentEvent:
    # Solo los campos del parche que el agente cambió: un null explícito quita un filtro.
    data = event.model_dump(mode="json", exclude_unset=isinstance(event, ActionEvent))
    return ServerSentEvent(event=EVENT_NAMES[type(event)], data=data)


@router.post("", response_class=EventSourceResponse)
async def ask_agent(
    body: AgentQuestion,
    model: Annotated[AgentModel, Depends(check_agent_allowed)],
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> AsyncIterable[ServerSentEvent]:
    """Agente del Radar. Stream SSE: `step`, `action`, `answer`, `error` y siempre `done`."""
    meter = UsageMeter()
    async with session_factory() as session:
        async for event in run_agent(body.question, model=model, session=session, meter=meter):
            yield _to_sse(event)
        await record_meter(session, meter)
