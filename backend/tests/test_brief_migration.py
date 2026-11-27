"""Migración que pasa los briefs al workspace de 30X, sobre un esquema creado con Alembic."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

from tests.conftest import TEST_URL

BACKEND_DIR = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "27e213f52e34"
OLD_USER = "8f1c2d3e-0000-4000-8000-000000000001"
OTHER_OLD_USER = "8f1c2d3e-0000-4000-8000-000000000002"


def alembic(*args: str) -> None:
    # En otro proceso: env.py lee la URL de los settings al importarse, y aquí va la de tests.
    env = {**os.environ, "DATABASE_URL": TEST_URL.render_as_string(hide_password=False)}
    subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND_DIR, env=env, check=True)


@pytest.fixture
async def engine_at_previous_revision(engine):
    # `engine` deja el esquema de create_all; aquí se rehace con las migraciones. El siguiente test
    # vuelve a crear el suyo con create_all, así que no hace falta restaurarlo.
    async with engine.begin() as conn:
        await conn.execute(text("drop schema public cascade"))
        await conn.execute(text("create schema public"))
    alembic("upgrade", PREVIOUS_REVISION)
    return engine


async def insert_old_chains(engine) -> None:
    async with engine.begin() as conn:
        for root, user in ((10, OLD_USER), (20, OTHER_OLD_USER)):
            for version in (1, 2):
                await conn.execute(
                    text(
                        "insert into editorial_briefs "
                        "(id, root_id, version, user_id, opportunity_id, run_id, request, brief) "
                        "values (:id, :root, :version, :user, 'opp_001', null, '{}', '{}')"
                    ),
                    {"id": root + version - 1, "root": root, "version": version, "user": user},
                )


async def test_existing_briefs_move_to_thirty_x_keeping_versions(engine_at_previous_revision):
    engine = engine_at_previous_revision
    await insert_old_chains(engine)

    alembic("upgrade", "head")

    async with engine.connect() as conn:
        workspace = (
            await conn.execute(
                text("select id, name, public_demo from workspaces where slug = '30x'")
            )
        ).one()
        rows = (
            await conn.execute(
                text(
                    "select id, root_id, version, workspace_id, created_by "
                    "from editorial_briefs order by id"
                )
            )
        ).all()
    assert (workspace.name, workspace.public_demo) == ("30X", True)
    assert [tuple(r) for r in rows] == [
        (10, 10, 1, workspace.id, OLD_USER),
        (11, 10, 2, workspace.id, OLD_USER),
        (20, 20, 1, workspace.id, OTHER_OLD_USER),
        (21, 20, 2, workspace.id, OTHER_OLD_USER),
    ]


async def test_existing_thirty_x_workspace_is_reused(engine_at_previous_revision):
    engine = engine_at_previous_revision
    async with engine.begin() as conn:
        workspace_id = await conn.scalar(
            text(
                "insert into workspaces (slug, name, public_demo) "
                "values ('30x', '30X', true) returning id"
            )
        )
    await insert_old_chains(engine)

    alembic("upgrade", "head")

    async with engine.connect() as conn:
        workspaces = await conn.scalar(text("select count(*) from workspaces"))
        moved = await conn.scalar(
            text("select count(*) from editorial_briefs where workspace_id = :w"),
            {"w": workspace_id},
        )
    assert (workspaces, moved) == (1, 4)


async def test_downgrade_gives_the_briefs_back_to_their_users(engine_at_previous_revision):
    engine = engine_at_previous_revision
    await insert_old_chains(engine)
    alembic("upgrade", "head")

    alembic("downgrade", PREVIOUS_REVISION)

    async with engine.connect() as conn:
        rows = (
            await conn.execute(text("select id, user_id from editorial_briefs order by id"))
        ).all()
        columns = await conn.scalars(
            text(
                "select column_name from information_schema.columns "
                "where table_name = 'editorial_briefs'"
            )
        )
        column_names = set(columns)
    assert [tuple(r) for r in rows] == [
        (10, OLD_USER),
        (11, OLD_USER),
        (20, OTHER_OLD_USER),
        (21, OTHER_OLD_USER),
    ]
    assert "workspace_id" not in column_names and "created_by" not in column_names
