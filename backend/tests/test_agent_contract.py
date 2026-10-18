import pytest
from pydantic import ValidationError

from app.schemas.agent import (
    MAX_HISTORY,
    ActionEvent,
    AgentQuestion,
    AgentScreen,
    DossierSection,
    Navigation,
    RadarPatch,
)


def test_question_alone_is_still_valid():
    body = AgentQuestion.model_validate({"question": "¿Qué acelera?"})

    assert body.history == []
    assert body.focus_ids == []
    assert body.view is None


def test_history_is_capped():
    with pytest.raises(ValidationError):
        AgentQuestion(question="¿Y ese?", history=["¿Qué acelera?"] * (MAX_HISTORY + 1))


def test_focus_ids_must_look_like_opportunity_ids():
    with pytest.raises(ValidationError):
        AgentQuestion(question="¿Y ese?", focus_ids=["DROP TABLE"])


def test_navigation_action_carries_only_what_was_set():
    event = ActionEvent(
        step_id=1,
        navigate=Navigation(
            screen=AgentScreen.DOSSIER, opportunity_id="opp_1", section=DossierSection.EVIDENCE
        ),
    )

    assert event.model_dump(mode="json", exclude_unset=True) == {
        "step_id": 1,
        "navigate": {"screen": "dossier", "opportunity_id": "opp_1", "section": "evidence"},
    }


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"patch": RadarPatch(selected="opp_1"), "navigate": Navigation(screen=AgentScreen.RADAR)},
    ],
    ids=["neither", "both"],
)
def test_action_needs_exactly_one_of_patch_or_navigate(fields):
    with pytest.raises(ValidationError):
        ActionEvent(step_id=1, **fields)


def test_explicit_null_recommendation_survives_serialization():
    event = ActionEvent(step_id=1, patch=RadarPatch(recommendation=None))

    assert event.model_dump(mode="json", exclude_unset=True) == {
        "step_id": 1,
        "patch": {"recommendation": None},
    }
