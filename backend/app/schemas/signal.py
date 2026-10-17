"""Contrato común de señales: lo que devuelve cualquier collector.

Es el contrato que consume Intelligence. Cambiarlo requiere avisar en el canal (CLAUDE.md §11).
"""

from datetime import datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field, HttpUrl


class Platform(StrEnum):
    YOUTUBE = "youtube"
    HACKERNEWS = "hackernews"
    RSS = "rss"
    BRAVE = "brave"
    # Solo vía sensor editorial (curación manual), nunca scraping.
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class Segment(StrEnum):
    """Para quién importa: quién publica/consume en esta fuente."""

    TECH = "tech"
    BUSINESS = "business"
    LATAM_ES = "latam_es"


class SourceKind(StrEnum):
    CHANNEL = "channel"  # canal de YouTube
    QUERY = "query"  # búsqueda (HN, Brave, YouTube search)
    FEED = "feed"  # RSS
    MANUAL = "manual"  # sensor editorial


class ContentFormat(StrEnum):
    SHORT_VIDEO = "short_video"
    LONG_VIDEO = "long_video"
    ARTICLE = "article"
    DISCUSSION = "discussion"
    CAROUSEL = "carousel"
    POST = "post"
    UNKNOWN = "unknown"


class Metrics(BaseModel):
    """Métricas públicas tal como las da la fuente. None = la fuente no la expone."""

    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    points: int | None = None  # Hacker News
    shares: int | None = None


class ContentSignal(BaseModel):
    platform: Platform
    external_id: str = Field(
        description="ID estable en la plataforma (video id, HN objectID, guid RSS)"
    )
    url: HttpUrl
    # Enlace al que apunta la pieza (p. ej. el artículo de una story de HN). Une fuentes.
    target_url: HttpUrl | None = None
    title: str
    description: str | None = Field(default=None, max_length=5000)
    # Nombre público del canal/medio/cuenta. Nunca datos personales de usuarios.
    author_name: str | None = None
    published_at: AwareDatetime
    observed_at: AwareDatetime
    format: ContentFormat = ContentFormat.UNKNOWN
    language: str | None = Field(default=None, description="ISO 639-1, p. ej. 'es', 'en'")
    duration_seconds: int | None = None
    metrics: Metrics = Field(default_factory=Metrics)


class SourceIn(BaseModel):
    platform: Platform
    kind: SourceKind
    external_id: str = Field(description="channel id, query o URL del feed")
    name: str
    url: HttpUrl | None = None
    segment: Segment
    language: str | None = None
    region: str | None = None


class SourceStatus(BaseModel):
    id: int
    platform: Platform
    name: str
    segment: Segment
    active: bool
    items: int
    last_observed_at: datetime | None


class SignalHit(BaseModel):
    """Una pieza recolectada que coincide con una búsqueda. Sin descripción ni autor (regla 1)."""

    url: HttpUrl
    title: str
    source: str = Field(description="Nombre de la fuente monitoreada (canal, medio o búsqueda)")
    platform: Platform
    segment: Segment
    region: str | None = Field(description="Región de la fuente; null = sin región asignada")
    language: str | None = Field(description="ISO 639-1; null = la fuente no lo indica")
    published_at: AwareDatetime
    observed_at: AwareDatetime = Field(
        description="Último snapshot de métricas o, sin snapshots, última vez que se vio la pieza"
    )
    metrics: Metrics = Field(description="Del último snapshot; null = no disponible, nunca 0")
    opportunity_ids: list[str] = Field(
        description="Oportunidades del ranking servido cuya evidencia incluye esta pieza"
    )
