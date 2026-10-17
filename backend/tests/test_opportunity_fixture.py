"""El fixture del frontend tiene que cumplir el contrato `Opportunity`. Sin DB."""

import json
from pathlib import Path

import pytest

from app.schemas.opportunity import (
    Collection,
    Evidence,
    FitCriterion,
    Opportunity,
    OpportunityList,
    OpportunityTimeline,
)

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


def test_breakdown_matches_score(raw):
    for o in OpportunityList.model_validate(raw["opportunities"]).items:
        if o.opportunity_score is None:
            assert o.score_breakdown is None
            continue
        b = o.score_breakdown
        assert b is not None
        weighted = sum(c.value * c.weight for c in b.components)
        weighted -= sum(p.points for p in b.penalties)
        assert b.total == o.opportunity_score
        assert b.total == pytest.approx(max(0, min(100, weighted)), abs=0.1)


def test_fit_criteria_match_fit_score(raw):
    for o in OpportunityList.model_validate(raw["opportunities"]).items:
        if o.audience_fit_criteria is None:
            continue
        assert o.audience_fit_score is not None
        assert {c.criterion for c in o.audience_fit_criteria} == set(FitCriterion)
        assert len(o.audience_fit_criteria) == len(FitCriterion)
        mean_level = sum(c.level for c in o.audience_fit_criteria) / len(o.audience_fit_criteria)
        assert mean_level / 5 * 100 == pytest.approx(o.audience_fit_score, abs=0.5)
        # La accionabilidad sale del criterio 6 (CLAUDE.md §7).
        [actionable] = [
            c for c in o.audience_fit_criteria if c.criterion is FitCriterion.ACTIONABLE_CONTENT
        ]
        assert o.actionability_score == pytest.approx(actionable.level / 5 * 100)
        urls = {e["url"] for e in raw["evidence"][o.id]}
        assert all(str(u) in urls for c in o.audience_fit_criteria for u in c.evidence_urls)


def test_old_payload_still_validates(raw):
    old_opportunity = dict(raw["opportunities"]["items"][0])
    for key in ("score_breakdown", "audience_fit_criteria"):
        old_opportunity.pop(key, None)
    old_evidence = dict(raw["evidence"]["opp_001"][0])
    for key in ("collection", "replica_of", "replica_count"):
        old_evidence.pop(key, None)

    o = Opportunity.model_validate(old_opportunity)
    e = Evidence.model_validate(old_evidence)

    assert o.score_breakdown is None
    assert o.audience_fit_criteria is None
    assert e.collection is Collection.AUTOMATIC
    assert e.replica_of is None
    assert e.replica_count == 0


def test_fixture_replicas_point_inside_their_topic(raw):
    replicas = 0
    for evidence in raw["evidence"].values():
        items = [Evidence.model_validate(e) for e in evidence]
        originals = {str(e.url): e for e in items if e.replica_of is None}
        for e in items:
            if e.replica_of is None:
                continue
            replicas += 1
            original = originals[str(e.replica_of)]
            assert original.replica_count >= 1
    assert replicas >= 1  # el fixture enseña al frontend al menos una republicación


def test_fixture_replicas_are_explained(raw):
    # Como en `build_opportunities`: si hay republicaciones, la descripción y las limitaciones
    # lo dicen.
    for o in OpportunityList.model_validate(raw["opportunities"]).items:
        if all(e["replica_of"] is None for e in raw["evidence"][o.id]):
            continue
        assert "republicación" in o.description
        assert any("republicación" in note for note in o.limitations)
