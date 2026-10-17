from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.signal import SourceStatus
from app.services import signals

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/status", response_model=list[SourceStatus])
async def sources_status(session: Annotated[AsyncSession, Depends(get_session)]):
    return await signals.sources_status(session)
