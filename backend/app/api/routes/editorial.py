import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.limits import GLOBAL_PER_DAY, PER_IP_PER_HOUR, LimitResult, RateLimiter
from app.api.auth import require_user_if_enabled
from app.api.routes.agent import client_ip
from app.api.workspace_access import (
    WorkspaceAccess,
    require_editor,
    workspace_access,
    workspace_access_if_exists,
)
from app.core.config import get_settings
from app.db.session import get_session
from app.editorial.briefs import Briefer, build_briefer
from app.schemas.editorial import (
    BriefCreate,
    BriefRequest,
    EditorialBrief,
    SavedBrief,
    SavedBriefSummary,
)
from app.services import editorial, user_briefs

router = APIRouter(prefix="/editorial", tags=["editorial"])

ERROR_STATUS: dict[type[editorial.BriefError], int] = {
    editorial.OpportunityNotFound: status.HTTP_404_NOT_FOUND,
    user_briefs.ParentBriefNotFound: status.HTTP_404_NOT_FOUND,
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
BRIEF_NOT_FOUND = "Brief no encontrado"
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
    body: BriefCreate,
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
    # En este orden: un 401 o un 404 no gastan el cupo de la IP. AUTH_REQUIRED frena aquí el gasto
    # en LLM; las lecturas del workspace siguen abiertas.
    dependencies=[
        Depends(require_user_if_enabled),
        Depends(workspace_access_if_exists),
        Depends(admit_brief),
    ],
)
async def create_brief(
    # Mismo nombre que en `admit_brief`: con otro, FastAPI esperaría dos cuerpos anidados.
    body: BriefCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    briefer: Annotated[Briefer | None, Depends(get_briefer)],
    # La misma dependencia que en `dependencies`: FastAPI la resuelve una vez y en ese orden.
    access: Annotated[WorkspaceAccess | None, Depends(workspace_access_if_exists)],
):
    """Brief de la oportunidad para una plataforma, un objetivo y un formato. Cacheado: la misma
    petición sobre la misma ejecución devuelve el mismo brief sin volver a llamar al LLM. Si lo pide
    un miembro del workspace se guarda como versión del equipo, esté o no activo AUTH_REQUIRED: con
    `parent_brief_id`, en la cadena de ese brief (404 si no es del workspace). Si ya hay una versión
    con la misma petición, se devuelve esa. Sin sesión o fuera del equipo, `id` y `version` son
    null."""
    # Fuera del equipo se devuelve sin guardar: el servicio solo guarda con los dos valores.
    # Sin la fila del workspace (deploy sin seed) tampoco hay equipo: el brief sale sin guardar.
    editor = access.user if access and access.can_edit else None
    try:
        return await user_briefs.create_brief(
            session,
            BriefRequest.model_validate(body.model_dump(exclude={"parent_brief_id"})),
            workspace_id=access.workspace.id if access and editor else None,
            created_by=editor.user_id if editor else None,
            parent_brief_id=body.parent_brief_id,
            briefer=briefer,
            now=datetime.now(UTC),
        )
    except editorial.BriefError as e:
        raise HTTPException(ERROR_STATUS[type(e)], str(e)) from e


# En un workspace público se leen sin sesión. El brief de otro workspace es un 404 y no un 403:
# así los ids no dicen qué briefs existen.
@router.get("/briefs", response_model=list[SavedBriefSummary])
async def list_saved_briefs(
    access: Annotated[WorkspaceAccess, Depends(workspace_access)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Una fila por cadena de versiones del workspace, con su última versión; más recientes
    primero (máximo 50)."""
    return await user_briefs.list_briefs(session, access.workspace.id)


@router.get(
    "/briefs/{brief_id}",
    response_model=SavedBrief,
    responses={status.HTTP_404_NOT_FOUND: {"description": ERROR_DESCRIPTION}},
)
async def read_saved_brief(
    brief_id: int,
    access: Annotated[WorkspaceAccess, Depends(workspace_access)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    saved = await user_briefs.get_brief(session, access.workspace.id, brief_id)
    if saved is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, BRIEF_NOT_FOUND)
    return saved


@router.delete(
    "/briefs/{brief_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        code: {"description": ERROR_DESCRIPTION}
        for code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]
    },
)
async def delete_saved_brief(
    brief_id: int,
    access: Annotated[WorkspaceAccess, Depends(require_editor)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Borra la cadena entera de versiones a la que pertenece el brief. Solo el equipo."""
    if not await user_briefs.delete_brief(session, access.workspace.id, brief_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, BRIEF_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
