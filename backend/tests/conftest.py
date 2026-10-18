import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import Base
from tests.test_opportunity_routes import add_run, fixture_results

# Los tests nunca derivan su DB de DATABASE_URL: puede apuntar a Supabase, que es la DB real.
# Por defecto, el Postgres de docker-compose.
DEFAULT_TEST_URL = "postgresql+asyncpg://radar:radar@localhost:5433/radar_test"
WORK_URL = make_url(get_settings().database_url)
TEST_URL = make_url(os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_URL))
# Para crear la DB de tests hace falta conectarse a otra del mismo servidor.
ADMIN_URL = TEST_URL.set(database="postgres")


@pytest.fixture
async def engine():
    admin = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        exists = await conn.scalar(
            text("select 1 from pg_database where datname = :n"), {"n": TEST_URL.database}
        )
        if not exists:
            await conn.execute(text(f'create database "{TEST_URL.database}"'))
    await admin.dispose()

    # El esquema se borra entero: nunca contra la DB de trabajo.
    same_server = (TEST_URL.host, TEST_URL.port) == (WORK_URL.host, WORK_URL.port)
    assert not (same_server and TEST_URL.database == WORK_URL.database), (
        "TEST_DATABASE_URL apunta a la DB de trabajo"
    )
    eng = create_async_engine(TEST_URL)
    async with eng.begin() as conn:
        # drop_all solo conoce las tablas de esta rama; las de otras ramas (p. ej. usage_events
        # con FK a pipeline_runs) bloquean el borrado.
        await conn.execute(text("drop schema public cascade"))
        await conn.execute(text("create schema public"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s


# Una ejecución servida con las oportunidades de data/fixtures/opportunities.json: la comparten los
# tests del agente (test_agent.py y test_agent_tools.py).
@pytest.fixture
async def seeded(session):
    await add_run(session, fixture_results())
