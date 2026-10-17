"""Contrato del brief editorial (`POST /editorial/brief`): lo consume la vista Create.

Cambiarlo rompe el trabajo de los demás: avisar en el canal antes. La petición solo lleva opciones
cerradas: no hay texto libre del usuario que llegue al LLM, y los briefs que se publican quedan
cacheados.
"""

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
