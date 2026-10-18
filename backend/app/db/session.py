from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# El pooler de Supabase en modo sesión (5432) admite 15 clientes entre la API, los jobs y cualquier
# script: con ~25 peticiones simultáneas la API respondía 500 (EMAXCONNSESSION). La API va por el
# modo transacción (6543), que reparte las conexiones por consulta; los jobs siguen en el 5432
# porque su lock (`pg_try_advisory_lock`) es de sesión. Con 8 como máximo, el resto espera turno.
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 3

# En modo transacción cada consulta puede caer en otra conexión del servidor, donde no existen los
# prepared statements de asyncpg: sin caché y con nombres únicos (doc de SQLAlchemy, "pgbouncer").
# En modo sesión no cambia nada.
POOLER_CONNECT_ARGS = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
}

engine = create_async_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    connect_args=POOLER_CONNECT_ARGS,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia de FastAPI."""
    async with SessionLocal() as session:
        yield session
