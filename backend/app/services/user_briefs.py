"""Briefs guardados de cada usuario, en cadenas de versiones: `POST /editorial/brief` con sesión
guarda una versión, y `GET /editorial/briefs` lista una fila por cadena del usuario del token.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.editorial.briefs import Briefer
from app.models import EditorialBriefRecord
from app.schemas.editorial import (
    BriefRequest,
    BriefVersion,
    EditorialBrief,
    SavedBrief,
    SavedBriefSummary,
)
from app.services.editorial import BriefError, generate_metered_brief
from app.services.opportunities import served_run_id

MAX_LISTED_BRIEFS = 50
FIRST_VERSION = 1
NEXT_ID = text("select nextval(pg_get_serial_sequence('editorial_briefs', 'id'))")
# Serializa los guardados de un mismo usuario: sin esto, dos peticiones iguales a la vez crearían
# dos cadenas o la misma versión dos veces. Se libera al hacer commit.
USER_LOCK = text("select pg_advisory_xact_lock(hashtext(:key))")


PARENT_NOT_FOUND = "Brief no encontrado"


class ParentBriefNotFound(BriefError):
    pass


Record = EditorialBriefRecord


@dataclass(frozen=True)
class _SavedVersion:
    id: int
    version: int


async def create_brief(
    session: AsyncSession,
    request: BriefRequest,
    *,
    user_id: str | None,
    parent_brief_id: int | None,
    briefer: Briefer | None,
    now: datetime,
) -> EditorialBrief:
    """El brief, guardado como versión a nombre de `user_id` si lo hay; sin usuario no se guarda
    (`id` y `version` None). `ParentBriefNotFound` si el padre no es un brief del usuario."""
    # Antes del LLM: un padre ajeno no gasta una llamada.
    if user_id is not None and parent_brief_id is not None:
        await _parent_root(session, user_id, parent_brief_id)
    brief = await generate_metered_brief(session, request, briefer=briefer, now=now)
    if user_id is None:
        return brief
    saved = await _save(session, request, brief, user_id=user_id, parent_brief_id=parent_brief_id)
    return brief.model_copy(update={"id": saved.id, "version": saved.version})


async def _save(
    session: AsyncSession,
    request: BriefRequest,
    brief: EditorialBrief,
    *,
    user_id: str,
    parent_brief_id: int | None,
) -> _SavedVersion:
    await session.execute(USER_LOCK, {"key": f"editorial_briefs:{user_id}"})
    request_json = request.model_dump(mode="json")
    run_id = await served_run_id(session)
    if parent_brief_id is None:
        same = Record.run_id.is_not_distinct_from(run_id)
        root_id = None
    else:
        root_id = await _parent_root(session, user_id, parent_brief_id)
        same = Record.root_id == root_id
    # Pedir lo mismo otra vez (p. ej. "Cambiar enfoque" sin cambios) devuelve la versión que ya hay.
    if existing := await _same_request(session, user_id, request_json, same):
        await session.commit()
        return existing
    record = await _new_version(session, root_id)
    record.user_id = user_id
    record.opportunity_id = request.opportunity_id
    record.run_id = run_id
    record.request = request_json
    record.brief = brief.model_dump(mode="json", exclude={"id", "version"})
    session.add(record)
    await session.flush()
    saved = _SavedVersion(record.id, record.version)
    await session.commit()
    return saved


async def _parent_root(session: AsyncSession, user_id: str, parent_brief_id: int) -> int:
    root_id = await session.scalar(
        select(Record.root_id).where(Record.id == parent_brief_id, Record.user_id == user_id)
    )
    if root_id is None:
        raise ParentBriefNotFound(PARENT_NOT_FOUND)
    return root_id


async def _same_request(
    session: AsyncSession, user_id: str, request_json: dict[str, Any], scope: ColumnElement[bool]
) -> _SavedVersion | None:
    row = (
        await session.execute(
            select(Record.id, Record.version)
            .where(Record.user_id == user_id, Record.request == request_json, scope)
            .order_by(Record.created_at.desc(), Record.id.desc())
            .limit(1)
        )
    ).first()
    return None if row is None else _SavedVersion(row.id, row.version)


async def _new_version(session: AsyncSession, root_id: int | None) -> EditorialBriefRecord:
    if root_id is None:
        # La primera versión es su propia raíz: el id se pide antes para poder repetirlo en root_id.
        new_id = await session.scalar(NEXT_ID)
        return Record(id=new_id, root_id=new_id, version=FIRST_VERSION)
    latest = await session.scalar(select(func.max(Record.version)).where(Record.root_id == root_id))
    return Record(root_id=root_id, version=(latest or 0) + 1)


async def list_briefs(session: AsyncSession, user_id: str) -> list[SavedBriefSummary]:
    chain = Record.root_id
    ranked = (
        select(
            Record,
            func.row_number()
            .over(partition_by=chain, order_by=Record.version.desc())
            .label("rank"),
            func.count().over(partition_by=chain).label("version_count"),
        )
        .where(Record.user_id == user_id)
        .subquery()
    )
    latest = aliased(Record, ranked)
    rows = await session.execute(
        select(latest, ranked.c.version_count)
        .where(ranked.c.rank == 1)
        # Desempate por id: dos filas de la misma transacción tienen el mismo `created_at`.
        .order_by(ranked.c.created_at.desc(), ranked.c.id.desc())
        .limit(MAX_LISTED_BRIEFS)
    )
    return [_summary(r, count) for r, count in rows]


async def get_brief(session: AsyncSession, user_id: str, brief_id: int) -> SavedBrief | None:
    """None si no existe o es de otro usuario: quien llama no puede distinguir los dos casos."""
    # El usuario va en la misma consulta: nunca se lee la fila de otro para compararla después.
    record = await session.scalar(
        select(Record).where(Record.id == brief_id, Record.user_id == user_id)
    )
    if record is None:
        return None
    chain = await session.scalars(
        select(Record)
        .where(Record.root_id == record.root_id, Record.user_id == user_id)
        .order_by(Record.version)
    )
    return SavedBrief(
        id=record.id,
        root_id=record.root_id,
        version=record.version,
        created_at=record.created_at,
        request=BriefRequest.model_validate(record.request),
        brief=EditorialBrief.model_validate(
            {**record.brief, "id": record.id, "version": record.version}
        ),
        versions=[_version(r) for r in chain],
    )


async def delete_brief(session: AsyncSession, user_id: str, brief_id: int) -> bool:
    """Borra la cadena entera del brief. False si no existe o es de otro usuario."""
    root_id = await session.scalar(
        select(Record.root_id).where(Record.id == brief_id, Record.user_id == user_id)
    )
    if root_id is None:
        return False
    await session.execute(
        delete(Record).where(Record.root_id == root_id, Record.user_id == user_id)
    )
    await session.commit()
    return True


def _version(r: EditorialBriefRecord) -> BriefVersion:
    request = BriefRequest.model_validate(r.request)
    return BriefVersion(
        id=r.id,
        version=r.version,
        platform=request.platform,
        goal=request.goal,
        format=request.format,
        created_at=r.created_at,
    )


def _summary(r: EditorialBriefRecord, version_count: int) -> SavedBriefSummary:
    request = BriefRequest.model_validate(r.request)
    return SavedBriefSummary(
        id=r.id,
        root_id=r.root_id,
        version=r.version,
        version_count=version_count,
        opportunity_id=r.opportunity_id,
        topic=r.brief["topic"],
        platform=request.platform,
        goal=request.goal,
        format=request.format,
        created_at=r.created_at,
    )
