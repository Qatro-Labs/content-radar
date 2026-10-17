import asyncio
import hashlib
import logging
from collections.abc import AsyncIterable, AsyncIterator, Callable
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
logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]
NOT_CONFIGURED = "El asistente no está configurado."
LIMIT_MESSAGES = {
    LimitResult.IP: "Has hecho demasiadas preguntas seguidas. Prueba en unos minutos.",
    LimitResult.GLOBAL: "El asistente ha alcanzado el límite de hoy. Prueba mañana.",
}
BUSY_MESSAGE = "El asistente está ocupado. Prueba en unos segundos."
UNKNOWN_CLIENT = "unknown"
# Preguntas a la vez en todo el proceso: cada una mantiene una llamada al LLM y una sesión de DB.
MAX_CONCURRENT_QUESTIONS = 4
# Lo justo para distinguir clientes en los logs sin guardar su IP (D15).
IP_HASH_CHARS = 12
EVENT_NAMES: dict[type, str] = {
    StepEvent: "step",
    ActionEvent: "action",
    AnswerEvent: "answer",
    ErrorEvent: "error",
    DoneEvent: "done",
}

_limiter = RateLimiter(per_ip_per_hour=PER_IP_PER_HOUR, global_per_day=GLOBAL_PER_DAY)
_slots = asyncio.Semaphore(MAX_CONCURRENT_QUESTIONS)
# Referencias fuertes a los registros de consumo en curso: el event loop solo guarda referencias
# débiles a sus tareas y una tarea sin referencias se puede recolectar a medias.
_pending_records: set[asyncio.Task[None]] = set()


@lru_cache
def get_agent_model() -> AgentModel | None:
    return build_agent_model(get_settings())


def get_rate_limiter() -> RateLimiter:
    return _limiter


def get_agent_slots() -> asyncio.Semaphore:
    return _slots


def get_session_factory() -> SessionFactory:
    # La vida de una dependencia con `yield` no cubre todo el stream: la sesión la abre el
    # generador (plan data-radar-agent, D7).
    return SessionLocal


def check_agent_allowed(
    # Sin uso aquí: obliga a FastAPI a validar el cuerpo antes, así un 422 no gasta cupo (D19).
    body: AgentQuestion,
    request: Request,
    model: Annotated[AgentModel | None, Depends(get_agent_model)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AgentModel:
    if model is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NOT_CONFIGURED)
    result = limiter.check(_client_ip(request), datetime.now(UTC))
    if result is not LimitResult.OK:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, LIMIT_MESSAGES[result])
    return model


async def hold_agent_slot(
    model: Annotated[AgentModel, Depends(check_agent_allowed)],
    slots: Annotated[asyncio.Semaphore, Depends(get_agent_slots)],
) -> AsyncIterator[AgentModel]:
    # Una dependencia con `yield` se cierra cuando termina el stream SSE (o el cliente se va):
    # el hueco se libera siempre.
    if slots.locked():
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, BUSY_MESSAGE)
    await slots.acquire()
    try:
        yield model
    finally:
        slots.release()


def _client_ip(request: Request) -> str:
    # Detrás del proxy de Railway, uvicorn ya pone aquí la IP real (--proxy-headers).
    return request.client.host if request.client else UNKNOWN_CLIENT


def _ip_hash(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:IP_HASH_CHARS]


async def _record_usage(meter: UsageMeter, session_factory: SessionFactory) -> None:
    if not meter.counts:
        return
    async with session_factory() as session:
        await record_meter(session, meter)


async def _record_usage_despite_cancel(meter: UsageMeter, session_factory: SessionFactory) -> None:
    # El LLM ya cobró aunque el usuario cierre la página: el registro sigue en su propia tarea y
    # con su propia sesión aunque cancelen el stream (D18).
    task = asyncio.create_task(_record_usage(meter, session_factory))
    _pending_records.add(task)
    task.add_done_callback(_pending_records.discard)
    await asyncio.shield(task)


def _to_sse(event: AgentEvent) -> ServerSentEvent:
    # Solo los campos del parche que el agente cambió: un null explícito quita un filtro.
    data = event.model_dump(mode="json", exclude_unset=isinstance(event, ActionEvent))
    return ServerSentEvent(event=EVENT_NAMES[type(event)], data=data)


# El generador emite `ServerSentEvent` para poner el nombre de cada evento, y FastAPI no documenta
# su `data`: se declara aquí para que los modelos lleguen a OpenAPI y a `frontend/src/types/api.ts`.
EVENTS_RESPONSE = {
    "model": AgentEvent,
    "description": (
        "Stream SSE. El `data` de cada evento es el modelo de su nombre: step → StepEvent, "
        "action → ActionEvent, answer → AnswerEvent, error → ErrorEvent, done → DoneEvent."
    ),
}


@router.post(
    "", response_class=EventSourceResponse, responses={status.HTTP_200_OK: EVENTS_RESPONSE}
)
async def ask_agent(
    body: AgentQuestion,
    request: Request,
    model: Annotated[AgentModel, Depends(hold_agent_slot)],
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> AsyncIterable[ServerSentEvent]:
    """Agente del Radar. Stream SSE: `step`, `action`, `answer`, `error` y siempre `done`."""
    meter = UsageMeter()
    steps = 0
    try:
        async with session_factory() as session:
            stream = run_agent(body.question, model=model, session=session, meter=meter)
            async for event in stream:
                if isinstance(event, DoneEvent):
                    steps = event.steps
                yield _to_sse(event)
    finally:
        await _record_usage_despite_cancel(meter, session_factory)
        # Nunca el texto de la pregunta ni la IP (D15).
        logger.info(
            "agent question chars=%d steps=%d ip_hash=%s",
            len(body.question),
            steps,
            _ip_hash(_client_ip(request)),
        )
