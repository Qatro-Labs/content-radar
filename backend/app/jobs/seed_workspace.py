"""Siembra el workspace público de 30X con su perfil de marca (versión 1).

    uv run python -m app.jobs.seed_workspace

Es idempotente: no toca un perfil que alguien ya haya editado.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal, engine
from app.models.workspaces import RadarProfileRecord, WorkspaceRecord
from app.schemas.editorial import BriefFormat, BriefGoal, BriefPlatform
from app.schemas.profile import PublishingDay, RadarProfile, Weekday

SLUG = "30x"

# Audiencia y fuera de alcance salen de data/audiences/30x.yaml (`audience.summary` y `not_for`).
# Los días son los valores por defecto de la spec, no la frecuencia real de 30X.
THIRTY_X_PROFILE = RadarProfile(
    creates_about="Crecimiento de empresas y aplicación de la IA con criterio y resultados",
    audience=(
        "Dueños, fundadores, CEOs y líderes de empresas de Latinoamérica que quieren hacer crecer "
        "su negocio y aplicar IA con criterio y resultados, sin depender de ellos mismos para todo "
        "y sin necesidad de saber programar."
    ),
    goal=BriefGoal.EDUCATE,
    target_region="Latinoamérica",
    languages=["es"],
    out_of_scope=(
        "Quien quiere aprender IA solo a nivel personal, programar o construir agentes a fondo, o "
        "buscar una habilidad técnica puntual (web, AI for Executives). En Instagram tampoco "
        "aparece contenido técnico."
    ),
    tone=["directo", "práctico"],
    call_to_action="",
    never_say="Promesas de resultados que la evidencia no muestra",
    publishing_days=[
        PublishingDay(
            day=Weekday.MON, channel=BriefPlatform.INSTAGRAM, format=BriefFormat.SHORT_VIDEO
        ),
        PublishingDay(
            day=Weekday.WED, channel=BriefPlatform.INSTAGRAM, format=BriefFormat.CAROUSEL
        ),
        PublishingDay(
            day=Weekday.FRI, channel=BriefPlatform.INSTAGRAM, format=BriefFormat.SHORT_VIDEO
        ),
    ],
)


async def seed_thirty_x(session: AsyncSession) -> WorkspaceRecord:
    workspace = await session.scalar(select(WorkspaceRecord).where(WorkspaceRecord.slug == SLUG))
    if workspace is None:
        workspace = WorkspaceRecord(slug=SLUG, name="30X", public_demo=True)
        session.add(workspace)
        await session.flush()

    has_profile = await session.scalar(
        select(RadarProfileRecord.id)
        .where(RadarProfileRecord.workspace_id == workspace.id)
        .limit(1)
    )
    if has_profile is None:
        session.add(
            RadarProfileRecord(
                workspace_id=workspace.id,
                version=1,
                profile=THIRTY_X_PROFILE.model_dump(mode="json"),
                created_by=None,
            )
        )
    await session.commit()
    return workspace


async def main() -> None:
    try:
        async with SessionLocal() as session:
            workspace = await seed_thirty_x(session)
        print(f"✓ workspace '{workspace.slug}' listo")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
