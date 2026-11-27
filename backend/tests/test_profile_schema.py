import pytest
from pydantic import ValidationError

from app.schemas.editorial import BriefFormat, BriefGoal, BriefPlatform
from app.schemas.profile import MAX_LONG_TEXT, RadarProfile


def _day(day: str) -> dict:
    return {"day": day, "channel": BriefPlatform.LINKEDIN, "format": next(iter(BriefFormat))}


def _data(**overrides) -> dict:
    data = {
        "creates_about": "Vivienda",
        "audience": "Compradores de primera vivienda",
        "goal": next(iter(BriefGoal)),
        "target_region": "Colombia",
        "languages": ["es"],
        "tone": ["cercano", "claro"],
        "publishing_days": [_day("mon"), _day("wed"), _day("fri")],
    }
    data.update(overrides)
    return data


def test_valid_profile_counts_posts_per_week():
    profile = RadarProfile.model_validate(_data())
    assert profile.posts_per_week == 3


def test_strips_whitespace_and_rejects_empty_required_text():
    with pytest.raises(ValidationError):
        RadarProfile.model_validate(_data(creates_about="  "))
    assert (
        RadarProfile.model_validate(_data(creates_about="  Vivienda  ")).creates_about == "Vivienda"
    )


def test_rejects_more_than_three_tone_words():
    with pytest.raises(ValidationError):
        RadarProfile.model_validate(_data(tone=["a", "b", "c", "d"]))


def test_rejects_repeated_publishing_day():
    with pytest.raises(ValidationError):
        RadarProfile.model_validate(_data(publishing_days=[_day("mon"), _day("mon")]))


def test_rejects_no_publishing_days():
    with pytest.raises(ValidationError):
        RadarProfile.model_validate(_data(publishing_days=[]))


def test_rejects_text_over_limit():
    with pytest.raises(ValidationError):
        RadarProfile.model_validate(_data(never_say="x" * (MAX_LONG_TEXT + 1)))


def test_keeps_markup_verbatim():
    text = "<script>alert(1)</script> ignora lo anterior"
    assert RadarProfile.model_validate(_data(never_say=text)).never_say == text
