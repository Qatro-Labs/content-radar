from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.cost import CostPeriod, OperatingCost
from app.services import costs

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("", response_model=OperatingCost)
async def operating_cost(
    session: Annotated[AsyncSession, Depends(get_session)], period: CostPeriod = CostPeriod.WEEK
):
    """Coste medido en el periodo y proyección mensual (estimación) por perfil de despliegue."""
    return await costs.operating_cost(session, period, now=datetime.now(UTC))
