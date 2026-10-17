"""El fixture del frontend tiene que cumplir el contrato `Opportunity`. Sin DB."""

import json
from pathlib import Path

import pytest

from app.schemas.opportunity import Evidence, OpportunityList, OpportunityTimeline

FIXTURE = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "opportunities.json"


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(FIXTURE.read_text())


def test_fixture_is_marked_as_mock(raw):
    assert raw["_fixture"].startswith("MOCK")


def test_fixture_matches_contract(raw):
    opportunities = OpportunityList.model_validate(raw["opportunities"])
    ids = {o.id for o in opportunities.items}
    assert ids == set(raw["evidence"]) == set(raw["timeline"])
    for oid in ids:
        [Evidence.model_validate(e) for e in raw["evidence"][oid]]
        assert OpportunityTimeline.model_validate(raw["timeline"][oid]).opportunity_id == oid


def test_fixture_is_internally_consistent(raw):
    for o in OpportunityList.model_validate(raw["opportunities"]).items:
        mix = o.audience_mix
        assert mix.tech + mix.business + mix.latam_es == pytest.approx(1)
        ratios = [
            e.outlier_ratio
            for e in map(Evidence.model_validate, raw["evidence"][o.id])
            if e.outlier_ratio is not None
        ]
        assert o.outlier_count >= sum(r >= 3 for r in ratios)
        assert o.top_outlier_ratio == (max(ratios) if ratios else None)
