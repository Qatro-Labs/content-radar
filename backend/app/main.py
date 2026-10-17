from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import costs, opportunities, sources
from app.core.config import get_settings
from app.db.session import get_session

settings = get_settings()

app = FastAPI(title="30X Signal API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(opportunities.router)
api_v1.include_router(sources.router)
api_v1.include_router(costs.router)
app.include_router(api_v1)


@app.get("/health", tags=["health"])
async def health(session: Annotated[AsyncSession, Depends(get_session)]):
    try:
        await session.execute(text("select 1"))
        db = "ok"
    except Exception:
        db = "unavailable"
    return {"status": "ok", "db": db, "env": settings.app_env}
