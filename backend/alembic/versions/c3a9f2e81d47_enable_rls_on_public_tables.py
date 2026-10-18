"""enable rls on public tables

La clave anon de Supabase va en el bundle del frontend. Sin RLS, con esa clave cualquiera lee y
escribe todas las tablas de `public` por la API REST de Supabase. RLS sin políticas lo cierra: los
roles anon y authenticated no ven ninguna fila. El backend se conecta como dueño de las tablas (o
postgres), que se salta RLS, y sigue funcionando igual.

Recorre las tablas que haya en `public` al aplicarla, `alembic_version` incluida: otras ramas
añaden tablas y una lista fija se quedaría corta. Una tabla creada después necesita su propio
`ENABLE ROW LEVEL SECURITY` en su migración.

Revision ID: c3a9f2e81d47
Revises: b7d41e9a2c05
Create Date: 2026-10-18 13:25:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c3a9f2e81d47"
down_revision: str | None = "b7d41e9a2c05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _set_rls(action: str) -> None:
    op.execute(f"""
        DO $$
        DECLARE t record;
        BEGIN
            FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                EXECUTE format('ALTER TABLE public.%I {action} ROW LEVEL SECURITY', t.tablename);
            END LOOP;
        END $$;
    """)


def upgrade() -> None:
    _set_rls("ENABLE")


def downgrade() -> None:
    _set_rls("DISABLE")
