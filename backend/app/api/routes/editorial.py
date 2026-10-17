from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.usage import UsageMeter
from app.core.config import get_settings
from app.db.session import get_session
from app.editorial.briefs import Briefer, build_briefer
from app.schemas.editorial import BriefRequest, EditorialBrief
from app.services import editorial
from app.services.costs import record_meter

router = APIRouter(prefix="/editorial", tags=["editorial"])

ERROR_STATUS: dict[type[editorial.BriefError], int] = {
    editorial.OpportunityNotFound: status.HTTP_404_NOT_FOUND,
    editorial.NoSafeEvidence: status.HTTP_409_CONFLICT,
    editorial.BriefFailed: status.HTTP_502_BAD_GATEWAY,
    editorial.BriefUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
}

ERROR_DESCRIPTION = "`detail` explica el motivo, en un texto que se puede mostrar"


@lru_cache
def get_briefer() -> Briefer | None:
    return build_briefer(get_settings())


@router.post(
    "/brief",
    response_model=EditorialBrief,
    responses={code: {"description": ERROR_DESCRIPTION} for code in ERROR_STATUS.values()},
)
async def create_brief(
    request: BriefRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    briefer: Annotated[Briefer | None, Depends(get_briefer)],
):
    """Brief de la oportunidad para una plataforma, un objetivo y un formato. Cacheado: la misma
    petición sobre la misma ejecución devuelve el mismo brief sin volver a llamar al LLM."""
    meter = UsageMeter()
    try:
        return await editorial.generate_brief(
            session, request, briefer=briefer, meter=meter, now=datetime.now(UTC)
        )
    except editorial.BriefError as e:
        raise HTTPException(ERROR_STATUS[type(e)], str(e)) from e
    finally:
        # El LLM cobra aunque el brief no supere la comprobación.
        if meter.counts:
            await record_meter(session, meter)
