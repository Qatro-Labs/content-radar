"""Del nivel de cada criterio del LLM a los scores y la recomendación. Sin DB ni LLM."""

from dataclasses import replace

from app.intelligence.audience_fit import (
    FIT_FAILED_NOTE,
    CriterionAssessment,
    actionability_score,
    apply_fit,
    audience_fit_score,
    mark_fit_failed,
)
from app.intelligence.lifecycle import Stage
from app.intelligence.opportunities import LLM_PENDING_NOTE, TopicResult
from app.schemas.opportunity import Confidence, FitCriterion, Lifecycle, Recommendation
from app.schemas.signal import Platform, Segment
from tests.test_build_opportunities import build_one, piece

# Niveles del ejemplo trabajado a mano: suma 19 → media 3,1667 → 63,3 sobre 100.
LEVELS = {
    FitCriterion.BUSINESS_IMPACT: 4,
    FitCriterion.ORG_APPLICATION: 3,
    FitCriterion.EXEC_READABILITY: 2,
    FitCriterion.LATAM_RELEVANCE: 1,
    FitCriterion.PILLAR_FIT: 4,
    FitCriterion.ACTIONABLE_CONTENT: 5,
}


def assessments(levels: dict[FitCriterion, int], urls: list[str]) -> list[CriterionAssessment]:
    return [
        CriterionAssessment(criterion=c, justification=f"Por {c.value}.", cited_urls=urls, level=n)
        for c, n in levels.items()
    ]


def sent(topic: TopicResult) -> set[str]:
    return {p.url for p in topic.pieces}


def emerging_topic() -> TopicResult:
    hn = [piece(i, hours_ago=5 + i * 6) for i in range(6)]
    rss = [
        piece(10 + i, hours_ago=3 + i, platform=Platform.RSS, source=f"Medio {i}",
              seg=Segment.LATAM_ES)
        for i in range(3)
    ]  # fmt: skip
    r = build_one(hn + rss)
    # Valores fijos para que el ejemplo de opportunity_score se pueda calcular a mano.
    fixed = r.opportunity.model_copy(
        update={
            "momentum_score": 50.0,
            "cross_source_score": 60.0,
            "saturation_score": 20.0,
            "source_count": 4,
            "confidence": Confidence.MEDIUM,
        }
    )
    return replace(r, opportunity=fixed, stage=Stage(Lifecycle.EMERGING, "regla emerging"))


def test_fit_is_mean_level_over_five():
    assert audience_fit_score(LEVELS) == 63.3
    assert audience_fit_score(dict.fromkeys(FitCriterion, 0)) == 0.0
    assert audience_fit_score(dict.fromkeys(FitCriterion, 5)) == 100.0


def test_actionability_is_the_actionable_content_level():
    assert actionability_score(LEVELS) == 100.0
    assert actionability_score({**LEVELS, FitCriterion.ACTIONABLE_CONTENT: 2}) == 40.0


def test_apply_fit_fills_scores_breakdown_and_publish_now():
    topic = emerging_topic()

    cited = assessments(LEVELS, ["https://example.com/0"])
    o = apply_fit(topic, cited, sent_urls=sent(topic)).opportunity

    assert (o.audience_fit_score, o.actionability_score) == (63.3, 100.0)
    # 0,30·50 + 0,25·63,3 + 0,20·60 + 0,15·(100 − 20) + 0,10·100 = 64,825; 9 piezas, 4 fuentes:
    # sin penalizaciones.
    assert o.opportunity_score == 64.8
    assert o.score_breakdown is not None and o.score_breakdown.total == 64.8
    assert o.recommendation is Recommendation.PUBLISH_NOW
    assert o.recommendation_reason is not None and o.recommendation_reason.startswith("Publicar")
    assert o.audience_fit_criteria is not None
    assert [c.criterion for c in o.audience_fit_criteria] == list(FitCriterion)
    assert LLM_PENDING_NOTE not in o.limitations


def test_low_fit_does_not_publish():
    topic = emerging_topic()
    o = apply_fit(
        topic, assessments(dict.fromkeys(FitCriterion, 2), []), sent_urls=sent(topic)
    ).opportunity
    assert o.audience_fit_score == 40.0
    # org_application = 2: hay caso, así que no espera; con fit 40 busca ángulo.
    assert o.recommendation is Recommendation.FIND_ANGLE


def test_citation_outside_the_topic_is_dropped_and_noted():
    cited = ["https://example.com/0", "https://otro-sitio.example/x"]

    topic = emerging_topic()
    o = apply_fit(topic, assessments(LEVELS, cited), sent_urls=sent(topic)).opportunity

    assert o.audience_fit_criteria is not None
    assert all(
        [str(u) for u in c.evidence_urls] == ["https://example.com/0"]
        for c in o.audience_fit_criteria
    )
    assert any("6 citas" in note for note in o.limitations)  # una por criterio


def test_citation_to_a_topic_piece_the_llm_did_not_receive_is_dropped():
    topic = emerging_topic()
    received = {"https://example.com/0"}
    not_sent = next(p.url for p in topic.pieces if p.url not in received)

    o = apply_fit(topic, assessments(LEVELS, [not_sent]), sent_urls=received).opportunity

    assert o.audience_fit_criteria is not None
    assert all(c.evidence_urls == [] for c in o.audience_fit_criteria)


def test_fit_without_a_real_case_waits_for_one():
    levels = {**LEVELS, FitCriterion.ORG_APPLICATION: 1}
    topic = emerging_topic()
    o = apply_fit(topic, assessments(levels, []), sent_urls=sent(topic)).opportunity
    assert o.recommendation is Recommendation.WAIT_FOR_CASE


def test_failed_fit_stays_null_with_limitation():
    o = mark_fit_failed(emerging_topic()).opportunity
    assert o.audience_fit_score is None and o.audience_fit_criteria is None
    assert o.opportunity_score is None
    assert FIT_FAILED_NOTE in o.limitations
    assert LLM_PENDING_NOTE not in o.limitations
