from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import agent, bulk, costs, editorial, opportunities, sources
from app.core.config import get_settings
from app.db.session import get_session
from app.mcp.server import build_mcp_app, build_mcp_server, production_deps

settings = get_settings()

# El sub-app se construye antes que FastAPI: `session_manager` solo existe tras construirlo, y el
# lifespan de un sub-app montado no corre solo.
mcp_server = build_mcp_server(production_deps(settings))
mcp_app = build_mcp_app(mcp_server, settings.mcp_public_url)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(title="30X Signal API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(opportunities.router)
api_v1.include_router(bulk.router)
api_v1.include_router(sources.router)
api_v1.include_router(costs.router)
api_v1.include_router(agent.router)
api_v1.include_router(editorial.router)
app.include_router(api_v1)


@app.get("/health", tags=["health"])
async def health(session: Annotated[AsyncSession, Depends(get_session)]):
    try:
        await session.execute(text("select 1"))
        db = "ok"
    except Exception:
        db = "unavailable"
    return {"status": "ok", "db": db, "env": settings.app_env}


# El último: las rutas de FastAPI se evalúan antes, y el sub-app solo responde en `/mcp` (montarlo
# en `/mcp` haría que `/mcp` sin barra devolviera una redirección 307 que algunos clientes no
# siguen en un POST).
app.mount("/", mcp_app)
