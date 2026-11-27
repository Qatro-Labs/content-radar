"""Añade o quita miembros del workspace (quién puede editar su perfil).

    uv run python -m app.jobs.workspace_members add --user-id <sub> --role owner|member
    uv run python -m app.jobs.workspace_members remove --user-id <sub> [--workspace 30x]

El `user-id` es el `sub` del token de Supabase.
"""

import argparse
import asyncio
import sys
from collections.abc import Sequence

from app.db.session import SessionFactory, SessionLocal, engine
from app.jobs.seed_workspace import SLUG
from app.services.workspaces import add_member, get_workspace, remove_member


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Añade o quita miembros del workspace")
    parser.add_argument("--workspace", default=SLUG)
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add")
    add.add_argument("--user-id", required=True)
    add.add_argument("--role", choices=["owner", "member"], required=True)
    remove = commands.add_parser("remove")
    remove.add_argument("--user-id", required=True)
    return parser


async def run(argv: Sequence[str], session_factory: SessionFactory) -> int:
    args = build_parser().parse_args(argv)
    async with session_factory() as session:
        workspace = await get_workspace(session, args.workspace)
        if workspace is None:
            print(f"✗ no existe el workspace '{args.workspace}'")
            return 1
        if args.command == "add":
            await add_member(session, workspace.id, args.user_id, args.role)
            print(f"✓ {args.user_id} es {args.role} de '{workspace.slug}'")
            return 0
        if await remove_member(session, workspace.id, args.user_id):
            print(f"✓ {args.user_id} ya no es miembro de '{workspace.slug}'")
            return 0
        print(f"✗ {args.user_id} no era miembro de '{workspace.slug}'")
        return 1


async def main() -> int:
    try:
        return await run(sys.argv[1:], SessionLocal)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
