"""Contrato del brief editorial (`POST /editorial/brief`): lo consume la vista Create.

Cambiarlo rompe el trabajo de los demás: avisar en el canal antes. La petición solo lleva opciones
cerradas: no hay texto libre del usuario que llegue al LLM, y los briefs que se publican quedan
cacheados.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.opportunity import Evidence, Recommendation


class BriefPlatform(StrEnum):
    # Dónde publica 30X, no de dónde recolectamos: la regla 2 trata de la recolección.
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    NEWSLETTER = "newsletter"


class BriefGoal(StrEnum):
    EDUCATE = "educate"
    SPARK_CONVERSATION = "spark_conversation"
    GENERATE_LEADS = "generate_leads"


class BriefFormat(StrEnum):
    POST = "post"
    CAROUSEL = "carousel"
    SHORT_VIDEO = "short_video"
    LONG_VIDEO = "long_video"
    ARTICLE = "article"


class BriefRequest(BaseModel):
    opportunity_id: str
    platform: BriefPlatform
    goal: BriefGoal
    format: BriefFormat


class BriefPoint(BaseModel):
    text: str
    evidence_urls: list[HttpUrl] = Field(min_length=1, description="Piezas que lo respaldan")


class EditorialBrief(BaseModel):
    id: int | None = Field(
        default=None, description="Id del brief guardado; None si no hay usuario y no se guardó"
    )
    version: int | None = Field(
        default=None, description="Versión dentro de su cadena; None si no se guardó"
    )
    opportunity_id: str
    topic: str
    platform: BriefPlatform
    goal: BriefGoal
    format: BriefFormat
    recommendation: Recommendation = Field(description="La de la oportunidad; el brief la respeta")
    recommendation_reason: str | None = None
    angle: str = Field(description="Ángulo propio de 30X para el tema")
    hook: str | None = Field(default=None, description="None si no superó la comprobación")
    structure: list[str] = Field(description="Pasos de la pieza, en orden")
    key_points: list[BriefPoint] = Field(min_length=1, description="Datos de la evidencia")
    why_it_fits: str | None = Field(
        default=None, description="Por qué encaja con la audiencia de 30X; None si no se comprobó"
    )
    evidence: list[Evidence] = Field(description="Las piezas que cita el brief")
    limitations: list[str]
    model: str


class BriefCreate(BriefRequest):
    """Cuerpo de `POST /editorial/brief`. Solo para la ruta: la tool MCP usa `BriefRequest` y el
    asistente no ve `parent_brief_id`."""

    parent_brief_id: int | None = Field(
        default=None,
        description="Brief del usuario del que se regenera: la nueva versión va a su cadena",
    )


class SavedBriefSummary(BaseModel):
    """Una fila por cadena de versiones, con los datos de la última."""

    id: int = Field(description="Id de la última versión")
    root_id: int
    version: int = Field(description="Número de la última versión")
    version_count: int
    opportunity_id: str
    topic: str = Field(description="El tema de la oportunidad cuando se generó el brief")
    platform: BriefPlatform
    goal: BriefGoal
    format: BriefFormat
    created_at: datetime = Field(description="Cuándo se guardó la última versión")


class BriefVersion(BaseModel):
    id: int
    version: int
    platform: BriefPlatform
    goal: BriefGoal
    format: BriefFormat
    created_at: datetime


class SavedBrief(BaseModel):
    id: int
    root_id: int
    version: int
    created_at: datetime
    request: BriefRequest
    brief: EditorialBrief
    versions: list[BriefVersion] = Field(description="Toda la cadena, por versión ascendente")
