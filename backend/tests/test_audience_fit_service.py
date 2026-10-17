"""Evaluación del audience fit de cada tema con caché en `llm_evaluations` (contra radar_test)."""

from dataclasses import replace

from sqlalchemy import func, select

from app.collectors.usage import UsageCount, UsageMeter
from app.editorial.audience import TopicEvaluation, TopicInput, system_prompt, user_message
from app.editorial.evaluator import EvaluationError, EvaluationResult
from app.intelligence.audience_fit import FIT_FAILED_NOTE
from app.models import LlmEvaluation
from app.schemas.cost import Provider
from app.services.audience_fit import EVALUATE_TOPIC_OPERATION, evaluate_topics
from tests.test_topic_evaluation import evaluation_json, safe, topic


class FakeEvaluator:
    def __init__(self, fail_labels: frozenset[str] = frozenset()) -> None:
        self.calls = 0
        self.fail_labels = fail_labels

    async def evaluate(self, topic: TopicInput) -> EvaluationResult:
        self.calls += 1
        if topic.label in self.fail_labels:
            raise EvaluationError("stop_reason=max_tokens")
        return EvaluationResult(
            model="claude-haiku-5-5",
            output=TopicEvaluation.model_validate(evaluation_json()),
            input_tokens=1800,
            output_tokens=700,
        )


def two_topics():
    first = topic()
    second = topic(7)
    # El rótulo es el título de una de sus piezas, como en `build_opportunities`.
    second.pieces[0] = replace(second.pieces[0], title="Segundo tema")
    second.opportunity = second.opportunity.model_copy(update={"topic": "Segundo tema"})
    answers = {p.item_id: safe() for r in (first, second) for p in r.pieces}
    return [first, second], answers


async def test_topics_get_fit_and_usage_is_metered(session):
    results, answers = two_topics()
    meter = UsageMeter()

    fitted, stats = await evaluate_topics(
        session, results, answers=answers, evaluator=FakeEvaluator(), meter=meter
    )

    assert (stats.evaluated, stats.cached, stats.failed) == (2, 0, 0)
    assert all(r.opportunity.audience_fit_score == 60.0 for r in fitted)  # nivel 3 en los seis
    assert meter.counts[(Provider.LLM_TEXT, EVALUATE_TOPIC_OPERATION)] == UsageCount(
        calls=2, units=3600, output_units=1400
    )


async def test_second_run_uses_cache_without_calls(session):
    results, answers = two_topics()
    await evaluate_topics(
        session, results, answers=answers, evaluator=FakeEvaluator(), meter=UsageMeter()
    )
    evaluator, meter = FakeEvaluator(), UsageMeter()

    fitted, stats = await evaluate_topics(
        session, results, answers=answers, evaluator=evaluator, meter=meter
    )

    assert evaluator.calls == 0
    assert (stats.evaluated, stats.cached) == (0, 2)
    assert not meter.counts
    assert all(r.opportunity.audience_fit_score == 60.0 for r in fitted)


async def test_failed_topic_is_null_with_limitation_and_not_cached(session):
    results, answers = two_topics()
    evaluator = FakeEvaluator(fail_labels=frozenset({"Segundo tema"}))

    fitted, stats = await evaluate_topics(
        session, results, answers=answers, evaluator=evaluator, meter=UsageMeter()
    )

    assert (stats.evaluated, stats.failed) == (1, 1)
    failed = fitted[1].opportunity
    assert failed.audience_fit_score is None and failed.opportunity_score is None
    assert FIT_FAILED_NOTE in failed.limitations
    assert await session.scalar(select(func.count()).select_from(LlmEvaluation)) == 1


async def test_topic_without_safe_pieces_is_not_sent(session):
    results, _ = two_topics()
    evaluator = FakeEvaluator()

    fitted, stats = await evaluate_topics(
        session, results, answers={}, evaluator=evaluator, meter=UsageMeter()
    )

    assert evaluator.calls == 0
    assert stats.without_evidence == 2
    assert all(FIT_FAILED_NOTE in r.opportunity.limitations for r in fitted)


async def test_without_evaluator_everything_stays_null(session):
    results, answers = two_topics()

    fitted, stats = await evaluate_topics(
        session, results, answers=answers, evaluator=None, meter=UsageMeter()
    )

    assert stats.skipped_reason
    assert all(r.opportunity.audience_fit_score is None for r in fitted)
    assert [r.opportunity for r in fitted] == [r.opportunity for r in results]


class PromptCheckingEvaluator(FakeEvaluator):
    def __init__(self, forbidden: str) -> None:
        super().__init__()
        self.forbidden = forbidden

    async def evaluate(self, topic: TopicInput) -> EvaluationResult:
        prompt = system_prompt() + user_message(topic)
        assert self.forbidden not in prompt, "texto de una pieza excluida en el prompt"
        return await super().evaluate(topic)


async def test_label_from_an_excluded_piece_never_reaches_the_prompt(session):
    result = topic()
    rep = result.pieces[0]
    # El tema se rotula con el título de una pieza que Jev marca como inyección.
    result.opportunity = result.opportunity.model_copy(update={"topic": rep.title})
    answers = {p.item_id: safe() for p in result.pieces[1:]}
    answers[rep.item_id] = {"injection": {"type": "noul", "noul": 0.9}}
    evaluator = PromptCheckingEvaluator(rep.title)

    _, stats = await evaluate_topics(
        session, [result], answers=answers, evaluator=evaluator, meter=UsageMeter()
    )

    assert (evaluator.calls, stats.evaluated) == (1, 1)
