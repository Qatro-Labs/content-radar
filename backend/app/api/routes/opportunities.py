from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.opportunity import (
    Confidence,
    Evidence,
    Lifecycle,
    Opportunity,
    OpportunityList,
    OpportunityTimeline,
    Period,
)
from app.services import opportunities

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

Session = Annotated[AsyncSession, Depends(get_session)]
NOT_FOUND = "Oportunidad no encontrada"


def _found[T](value: T | None) -> T:
    if value is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return value


@router.get("", response_model=OpportunityList | None)
async def list_opportunities(
    session: Session,
    # `analyze` solo calcula ventanas de 3 + 3 días: el campo `period` de la respuesta dice
    # el periodo real. Se acepta para que el filtro de la URL del Radar no rompa la llamada.
    period: Annotated[
        Period, Query(description="Solo se calcula 7d; la respuesta indica el periodo real")
    ] = Period.D7,
    lifecycle: Lifecycle | None = None,
    confidence: Confidence | None = None,
    topic: Annotated[str | None, Query(description="Subcadena del tema, sin mayúsculas")] = None,
):
    """`null` si todavía no hay ninguna ejecución correcta de `analyze`."""
    return await opportunities.list_opportunities(
        session, lifecycle=lifecycle, confidence=confidence, topic=topic
    )


@router.get("/{opportunity_id}", response_model=Opportunity)
async def get_opportunity(opportunity_id: str, session: Session):
    return _found(await opportunities.get_opportunity(session, opportunity_id))


@router.get("/{opportunity_id}/evidence", response_model=list[Evidence])
async def get_evidence(opportunity_id: str, session: Session):
    return _found(await opportunities.get_evidence(session, opportunity_id))


@router.get("/{opportunity_id}/timeline", response_model=OpportunityTimeline)
async def get_timeline(opportunity_id: str, session: Session):
    return _found(await opportunities.get_timeline(session, opportunity_id))
