"""Briefs guardados de cada usuario: `POST /editorial/brief` con sesión guarda una fila, y
`GET /editorial/briefs` lista solo las del usuario del token.
"""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.editorial.briefs import Briefer
from app.models import EditorialBriefRecord
from app.schemas.editorial import BriefRequest, EditorialBrief, SavedBrief, SavedBriefSummary
from app.services.editorial import generate_metered_brief
from app.services.opportunities import served_run_id

MAX_LISTED_BRIEFS = 50


async def create_brief(
    session: AsyncSession,
    request: BriefRequest,
    *,
    user_id: str | None,
    briefer: Briefer | None,
    now: datetime,
) -> EditorialBrief:
    """El brief, guardado a nombre de `user_id` si lo hay; sin usuario no se guarda (`id` None)."""
    brief = await generate_metered_brief(session, request, briefer=briefer, now=now)
    if user_id is None:
        return brief
    # Una fila por usuario aunque el contenido salga de la caché del LLM.
    record = EditorialBriefRecord(
        user_id=user_id,
        opportunity_id=request.opportunity_id,
        run_id=await served_run_id(session),
        request=request.model_dump(mode="json"),
        brief=brief.model_dump(mode="json", exclude={"id"}),
    )
    session.add(record)
    await session.flush()
    brief_id = record.id
    await session.commit()
    return brief.model_copy(update={"id": brief_id})


async def list_briefs(session: AsyncSession, user_id: str) -> list[SavedBriefSummary]:
    rows = await session.scalars(
        select(EditorialBriefRecord)
        .where(EditorialBriefRecord.user_id == user_id)
        # Desempate por id: dos filas de la misma transacción tienen el mismo `created_at`.
        .order_by(EditorialBriefRecord.created_at.desc(), EditorialBriefRecord.id.desc())
        .limit(MAX_LISTED_BRIEFS)
    )
    return [_summary(r) for r in rows]


async def get_brief(session: AsyncSession, user_id: str, brief_id: int) -> SavedBrief | None:
    """None si no existe o es de otro usuario: quien llama no puede distinguir los dos casos."""
    # El usuario va en la misma consulta: nunca se lee la fila de otro para compararla después.
    record = await session.scalar(
        select(EditorialBriefRecord).where(
            EditorialBriefRecord.id == brief_id, EditorialBriefRecord.user_id == user_id
        )
    )
    if record is None:
        return None
    return SavedBrief(
        id=record.id,
        created_at=record.created_at,
        request=BriefRequest.model_validate(record.request),
        brief=EditorialBrief.model_validate({**record.brief, "id": record.id}),
    )


async def delete_brief(session: AsyncSession, user_id: str, brief_id: int) -> bool:
    """False si no existe o es de otro usuario."""
    deleted = await session.scalar(
        delete(EditorialBriefRecord)
        .where(EditorialBriefRecord.id == brief_id, EditorialBriefRecord.user_id == user_id)
        .returning(EditorialBriefRecord.id)
    )
    await session.commit()
    return deleted is not None


def _summary(r: EditorialBriefRecord) -> SavedBriefSummary:
    request = BriefRequest.model_validate(r.request)
    return SavedBriefSummary(
        id=r.id,
        opportunity_id=r.opportunity_id,
        topic=r.brief["topic"],
        platform=request.platform,
        goal=request.goal,
        format=request.format,
        created_at=r.created_at,
    )
