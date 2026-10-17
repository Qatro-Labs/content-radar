import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import Base

# Base de datos aparte para tests, en el mismo servidor que DATABASE_URL.
BASE_URL = make_url(get_settings().database_url)
_raw_test_url = os.environ.get("TEST_DATABASE_URL")
TEST_URL = make_url(_raw_test_url) if _raw_test_url else BASE_URL.set(database="radar_test")


@pytest.fixture
async def engine():
    admin = create_async_engine(BASE_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        exists = await conn.scalar(
            text("select 1 from pg_database where datname = :n"), {"n": TEST_URL.database}
        )
        if not exists:
            await conn.execute(text(f'create database "{TEST_URL.database}"'))
    await admin.dispose()

    # El esquema se borra entero: nunca contra la DB de trabajo.
    assert TEST_URL.database != BASE_URL.database, "TEST_DATABASE_URL apunta a la DB de trabajo"
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
