"""Verificación de afirmaciones con la batería `claim` de Jev y su caché (contra radar_test)."""

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from app.collectors.usage import UsageMeter
from app.core.config import Settings
from app.intelligence.explanation import ClaimDraft
from app.intelligence.jev import CitedEvidence, JudgeError, JudgeResult, claim_state
from app.models import JevJudgment
from app.schemas.cost import Provider
from app.services.classification import SKIPPED_WITHOUT_KEY
from app.services.verification import (
    ClaimCheck,
    ClaimVerifier,
    build_claim_verifier,
    claim_cache_key,
    verify_claims,
)

SUPPORTED = "Las empresas usan agentes de IA en ventas."
REJECTED = "McKinsey confirma que el 80 % de las empresas los usa."
EVIDENCE = [CitedEvidence("Canal Ejemplo", "Agentes de IA en ventas", None)]


def answer(label: str, confidence: float = 0.9) -> dict[str, Any]:
    return {
        "type": "choice",
        "choice": label,
        "confidence": confidence,
        "probabilities": {label: confidence},
    }


class FakeClaimJudge:
    def __init__(self, *, rejected: frozenset[str] = frozenset({REJECTED}), fail: str = ""):
        self.rejected, self.fail = rejected, fail
        self.states: list[dict[str, Any]] = []

    @property
    def calls(self) -> int:
        return len(self.states)

    async def judge(self, state: dict[str, Any], questions: Mapping[str, Any]) -> JudgeResult:
        self.states.append(state)
        if state["claim"] == self.fail:
            raise JudgeError("rate limited")
        label = "says_nothing" if state["claim"] in self.rejected else "supports"
        answers = {"support": answer(label), "support_rev": answer(label)}
        return JudgeResult(model="jev-1.13.0", answers=answers, input_tokens=800, output_tokens=6)


def check(text: str, topic_index: int = 0) -> ClaimCheck:
    state = claim_state(text, facts=["Etapa: emergente."], evidence=EVIDENCE)
    return ClaimCheck(topic_index, ClaimDraft(text, ["https://example.com/0"]), state)


def key(c: ClaimCheck) -> str:
    return claim_cache_key(c.state)


async def verify(session, checks, judge, *, budget: int = 200, meter: UsageMeter | None = None):
    verifier = ClaimVerifier(judge=judge, budget=budget)
    return await verify_claims(session, checks, verifier=verifier, meter=meter or UsageMeter())


async def test_verdicts_are_cached_and_a_second_run_makes_no_calls(session):
    checks = [check(SUPPORTED), check(REJECTED)]
    first = FakeClaimJudge()
    verdicts, stats = await verify(session, checks, first)
    again = FakeClaimJudge()
    cached, cached_stats = await verify(session, checks, again)

    assert verdicts == {key(checks[0]): True, key(checks[1]): False}
    assert (first.calls, stats.verified, stats.rejected) == (2, 2, 1)
    assert cached == verdicts
    assert (again.calls, cached_stats.cached) == (0, 2)
    row = (await session.scalars(select(JevJudgment))).first()
    assert row is not None and row.battery == "claim" and row.content_item_id is None


async def test_usage_counted_only_for_real_calls(session):
    checks = [check(SUPPORTED), check(REJECTED)]
    meter = UsageMeter()
    await verify(session, checks, FakeClaimJudge(), meter=meter)
    await verify(session, checks, FakeClaimJudge(), meter=meter)

    count = meter.counts[(Provider.TYPESAFE_JEV, "claim_battery")]
    assert (count.calls, count.units) == (2, 1600)


async def test_jev_error_leaves_that_claim_without_verdict(session):
    checks = [check(SUPPORTED), check(REJECTED, topic_index=1)]

    verdicts, stats = await verify(session, checks, FakeClaimJudge(fail=REJECTED))

    assert verdicts == {key(checks[0]): True, key(checks[1]): None}
    assert (stats.failed, stats.unverified_topics) == (1, 1)
    assert await session.scalar(select(JevJudgment.cache_key)) == key(checks[0])


async def test_budget_limits_new_calls(session):
    checks = [check(SUPPORTED), check(REJECTED)]
    judge = FakeClaimJudge()

    verdicts, stats = await verify(session, checks, judge, budget=1)

    assert judge.calls == 1
    assert verdicts == {key(checks[0]): True, key(checks[1]): None}
    assert stats.over_budget == 1


async def test_without_judge_cached_verdicts_are_used_and_the_rest_have_none(session):
    await verify(session, [check(SUPPORTED)], FakeClaimJudge())
    checks = [check(SUPPORTED), check(REJECTED, topic_index=1)]

    verdicts, stats = await verify(session, checks, None)

    assert verdicts == {key(checks[0]): True, key(checks[1]): None}
    assert (stats.cached, stats.unverified_topics) == (1, 1)
    assert stats.skipped_reason == SKIPPED_WITHOUT_KEY


async def test_identical_states_share_one_call(session):
    judge = FakeClaimJudge()

    verdicts, _ = await verify(session, [check(SUPPORTED), check(SUPPORTED, 1)], judge)

    assert judge.calls == 1
    assert list(verdicts.values()) == [True]


def test_build_claim_verifier():
    off = Settings(jev_verify_claims=False, typesafe_api_key="")
    on = Settings(jev_verify_claims=True, typesafe_api_key="")

    assert build_claim_verifier(off) is None
    assert build_claim_verifier(on) == ClaimVerifier(judge=None)


def test_empty_verify_flag_falls_back_to_on(monkeypatch, tmp_path):
    # `JEV_VERIFY_CLAIMS=` vacío en Railway no debe impedir que arranquen la API y los jobs.
    monkeypatch.chdir(tmp_path)  # sin el .env local
    monkeypatch.setenv("JEV_VERIFY_CLAIMS", "")
    assert Settings().jev_verify_claims is True
