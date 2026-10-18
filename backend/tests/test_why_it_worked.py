from dataclasses import replace

import pytest

from app.intelligence.why_it_worked import outlier_hooks, with_outlier_hooks
from tests.test_build_opportunities import piece
from tests.test_opportunity_routes import fixture_results

OUT, NORMAL = 4.0, 1.0


def lifted(samples):
    result = outlier_hooks(samples)
    assert result is not None
    return result


def by_hook(result):
    assert result is not None
    return {h.hook: h for h in result.hooks}


def test_documented_example_is_an_observed_pattern():
    # docs/jev.md: 3 de 4 outliers con «dato», frente a 3 de 10 del resto → lift 2,5.
    samples = [(OUT, "data")] * 3 + [(OUT, "news")]
    samples += [(NORMAL, "data")] * 3 + [(NORMAL, "news")] * 7
    hooks = by_hook(lifted(samples))
    assert hooks["data"].lift == 2.5
    assert hooks["data"].observed_pattern
    assert (hooks["data"].outliers_with, hooks["data"].outliers_total) == (3, 4)
    assert (hooks["data"].rest_with, hooks["data"].rest_total) == (3, 10)
    # 1 de 4 frente a 7 de 10: lift 0,36, anecdótico.
    assert hooks["news"].lift == 0.36
    assert not hooks["news"].observed_pattern


def test_most_used_hook_comes_first():
    samples = [(OUT, "news"), (OUT, "data"), (OUT, "data"), (NORMAL, "news"), (NORMAL, "news")]
    assert [h.hook for h in lifted(samples).hooks] == ["data", "news"]


@pytest.mark.parametrize(
    "samples",
    [
        [],
        [(NORMAL, "data"), (NORMAL, "news")],
        [(None, "data"), (None, "news")],
        [(OUT, None), (NORMAL, "data")],
    ],
    ids=["empty", "no-outliers", "no-ratios", "outlier-hooks-undecided"],
)
def test_without_classified_outliers_there_is_nothing_to_say(samples):
    assert outlier_hooks(samples) is None


def test_single_outlier_is_anecdotal_even_with_high_lift():
    samples = [(OUT, "data"), (NORMAL, "news"), (NORMAL, "news"), (NORMAL, "news")]
    [hook] = lifted(samples).hooks
    assert hook.lift is None  # nadie del resto usa «dato»
    assert not hook.observed_pattern


def test_hook_only_outliers_use_is_a_pattern_without_lift():
    samples = [(OUT, "data"), (OUT, "data"), (NORMAL, "news"), (NORMAL, "news")]
    [hook] = lifted(samples).hooks
    assert hook.lift is None
    assert hook.observed_pattern


def test_too_small_rest_is_not_a_pattern():
    samples = [(OUT, "data"), (OUT, "data"), (NORMAL, "news")]
    [hook] = lifted(samples).hooks
    assert not hook.observed_pattern


def test_pieces_without_ratio_or_hook_are_left_out():
    samples = [(OUT, "data"), (OUT, "data"), (OUT, None), (None, "data")]
    samples += [(NORMAL, "news"), (NORMAL, "news"), (NORMAL, None)]
    result = lifted(samples)
    [hook] = result.hooks
    assert (hook.outliers_total, hook.rest_total) == (2, 2)
    assert result.outliers_unclassified == 1


def test_replicas_do_not_count():
    # La 3 republica la 1: copia su título y, con él, su gancho.
    pieces = [piece(i, hours_ago=i) for i in (1, 2, 3, 4, 5)]
    ratios = {1: OUT, 2: OUT, 3: OUT, 4: NORMAL, 5: NORMAL}
    hooks = {1: "data", 2: "news", 3: "data", 4: "data", 5: "news"}
    base = fixture_results()[0]
    topic = replace(base, pieces=pieces, ratios=ratios, replica_ids=frozenset({3}))
    [result] = with_outlier_hooks([topic], hooks)
    data = by_hook(result.opportunity.outlier_hooks)["data"]
    assert (data.outliers_with, data.outliers_total) == (1, 2)
    assert result.opportunity.id == base.opportunity.id
