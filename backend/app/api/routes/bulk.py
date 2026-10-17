from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.opportunity import OpportunityTimeline, TopicEvidence
from app.services import opportunities

# Lecturas en bloque de la ejecución servida, para no pedir evidencia y timeline tema a tema.
router = APIRouter(tags=["opportunities"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/evidence", response_model=list[TopicEvidence] | None)
async def list_all_evidence(session: Session):
    """Evidencia de todas las oportunidades, por `outlier_ratio` descendente (nulos al final; en
    empate, la más reciente). `null` si todavía no hay ninguna ejecución correcta de `analyze`."""
    return await opportunities.list_all_evidence(session)


@router.get("/timelines", response_model=list[OpportunityTimeline] | None)
async def list_timelines(session: Session):
    """Timelines de todas las oportunidades, en el orden del ranking. `null` si todavía no hay
    ninguna ejecución correcta de `analyze`."""
    return await opportunities.list_timelines(session)
