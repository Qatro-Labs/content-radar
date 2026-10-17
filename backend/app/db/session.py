from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia de FastAPI."""
    async with SessionLocal() as session:
        yield session
