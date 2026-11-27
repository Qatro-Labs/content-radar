"""Contrato del perfil de marca del Radar y del workspace que lo contiene.

Lo consumen la API de perfil y la vista de configuración. Cambiarlo rompe el trabajo de los demás:
avisar en el canal antes.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.schemas.editorial import BriefFormat, BriefGoal, BriefPlatform

MAX_TONE_WORDS = 3
MAX_TONE_WORD_CHARS = 30
MAX_SHORT_TEXT = 200
MAX_LONG_TEXT = 600
MAX_PUBLISHING_DAYS = 7
MAX_LANGUAGES = 3

# El texto del perfil llega al LLM como dato delimitado (regla 6), así que no se sanea el marcado:
# se guarda tal cual y solo se recortan los espacios.
RequiredShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SHORT_TEXT)
]
RequiredLongText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_LONG_TEXT)
]
OptionalShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=MAX_SHORT_TEXT)
]
OptionalLongText = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=MAX_LONG_TEXT)
]
ToneWord = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TONE_WORD_CHARS)
]
LanguageCode = Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")]


class Weekday(StrEnum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


class PublishingDay(BaseModel):
    day: Weekday
    channel: BriefPlatform
    format: BriefFormat


class RadarProfile(BaseModel):
    creates_about: RequiredShortText
    # La audiencia describe público y situación; el perfil de 30X ronda los 230 caracteres.
    audience: RequiredLongText
    goal: BriefGoal
    target_region: RequiredShortText
    languages: list[LanguageCode] = Field(min_length=1, max_length=MAX_LANGUAGES)
    out_of_scope: OptionalLongText = ""
    tone: list[ToneWord] = Field(min_length=1, max_length=MAX_TONE_WORDS)
    call_to_action: OptionalShortText = ""
    never_say: OptionalLongText = ""
    publishing_days: list[PublishingDay] = Field(min_length=1, max_length=MAX_PUBLISHING_DAYS)

    @field_validator("publishing_days")
    @classmethod
    def _days_are_unique(cls, value: list[PublishingDay]) -> list[PublishingDay]:
        days = [entry.day for entry in value]
        if len(days) != len(set(days)):
            raise ValueError("publishing_days no admite días repetidos")
        return value

    @property
    def posts_per_week(self) -> int:
        return len(self.publishing_days)


class WorkspaceRead(BaseModel):
    slug: str
    name: str
    public_demo: bool
    role: Literal["owner", "member"] | None


class ProfileRead(BaseModel):
    profile: RadarProfile
    version: int
    updated_at: datetime
    can_edit: bool


class ProfileUpdate(BaseModel):
    profile: RadarProfile
    expected_version: int
