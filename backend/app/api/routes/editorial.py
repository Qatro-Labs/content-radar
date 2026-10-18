import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.limits import GLOBAL_PER_DAY, PER_IP_PER_HOUR, LimitResult, RateLimiter
from app.api.auth import require_user_if_enabled
from app.api.routes.agent import client_ip
from app.core.config import get_settings
from app.db.session import get_session
from app.editorial.briefs import Briefer, build_briefer
from app.schemas.editorial import BriefRequest, EditorialBrief
from app.services import editorial

router = APIRouter(prefix="/editorial", tags=["editorial"])

ERROR_STATUS: dict[type[editorial.BriefError], int] = {
    editorial.OpportunityNotFound: status.HTTP_404_NOT_FOUND,
    editorial.NoSafeEvidence: status.HTTP_409_CONFLICT,
    editorial.BriefFailed: status.HTTP_502_BAD_GATEWAY,
    editorial.BriefUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
}

ERROR_DESCRIPTION = "`detail` explica el motivo, en un texto que se puede mostrar"
LIMIT_MESSAGES = {
    LimitResult.IP: "Has pedido demasiados briefs seguidos. Prueba en unos minutos.",
    LimitResult.GLOBAL: "Se alcanzó el límite de briefs de hoy. Prueba mañana.",
}
BUSY_MESSAGE = "Se están generando otros briefs. Prueba en unos segundos."
MAX_CONCURRENT_BRIEFS = 4

# Un brief rechazado por la comprobación no se cachea y volver a pedirlo vuelve a llamar al LLM:
# los mismos límites que el agente, con su propio cupo.
_limiter = RateLimiter(per_ip_per_hour=PER_IP_PER_HOUR, global_per_day=GLOBAL_PER_DAY)
_slots = asyncio.Semaphore(MAX_CONCURRENT_BRIEFS)


@lru_cache
def get_briefer() -> Briefer | None:
    return build_briefer(get_settings())


def get_brief_limiter() -> RateLimiter:
    return _limiter


async def admit_brief(
    # Sin uso aquí: obliga a FastAPI a validar el cuerpo antes, así un 422 no gasta cupo.
    body: BriefRequest,
    request: Request,
    limiter: Annotated[RateLimiter, Depends(get_brief_limiter)],
) -> AsyncIterator[None]:
    if _slots.locked():
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, BUSY_MESSAGE)
    async with _slots:
        result = limiter.check(client_ip(request), datetime.now(UTC))
        if result is not LimitResult.OK:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, LIMIT_MESSAGES[result])
        yield


@router.post(
    "/brief",
    response_model=EditorialBrief,
    responses={
        code: {"description": ERROR_DESCRIPTION}
        for code in [*ERROR_STATUS.values(), status.HTTP_429_TOO_MANY_REQUESTS]
    },
    # En este orden: un 401 no gasta el cupo de la IP.
    dependencies=[Depends(require_user_if_enabled), Depends(admit_brief)],
)
async def create_brief(
    # Mismo nombre que en `admit_brief`: con otro, FastAPI esperaría dos cuerpos anidados.
    body: BriefRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    briefer: Annotated[Briefer | None, Depends(get_briefer)],
):
    """Brief de la oportunidad para una plataforma, un objetivo y un formato. Cacheado: la misma
    petición sobre la misma ejecución devuelve el mismo brief sin volver a llamar al LLM."""
    try:
        return await editorial.generate_metered_brief(
            session, body, briefer=briefer, now=datetime.now(UTC)
        )
    except editorial.BriefError as e:
        raise HTTPException(ERROR_STATUS[type(e)], str(e)) from e
