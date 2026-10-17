"""Republicaciones de la misma nota dentro de un tema: lógica pura, sin DB ni Jev."""

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from app.intelligence.opportunities import Piece
from app.intelligence.replicas import (
    NO_REPLICAS,
    CandidatePair,
    ReplicaBasis,
    ReplicaEdge,
    decide_pair,
    group_stories,
    normalize_title,
    replica_notes,
    replica_outlets,
    same_link,
    same_story_verdict,
    same_title,
    topic_pairs,
)
from app.schemas.signal import Metrics, Platform, Segment, SourceKind

AS_OF = datetime(2026, 10, 17, 12, tzinfo=UTC)
LONG_TITLE = "OpenAI publica su informe anual de seguridad"


def piece(
    i,
    *,
    source="Medio A",
    platform=Platform.RSS,
    title=None,
    url=None,
    target_url=None,
    hours_ago=10,
):
    return Piece(
        item_id=i,
        url=url or f"https://example.com/{i}",
        title=title or f"Pieza {i}",
        description=None,
        platform=platform,
        source_id=hash(source) % 1000,
        source_name=source,
        segment=Segment.TECH,
        language="en",
        published_at=AS_OF - timedelta(hours=hours_ago),
        observed_at=AS_OF,
        metrics=Metrics(),
        source_kind=SourceKind.FEED,
        target_url=target_url,
    )


def unit(similarity_to_first: float) -> list[float]:
    # Vector unitario con producto escalar exacto frente a [1, 0].
    return [similarity_to_first, math.sqrt(1 - similarity_to_first**2)]


def vectors(*similarities: float) -> np.ndarray:
    return np.array([unit(s) for s in similarities])


def test_normalize_title_ignores_case_quotes_and_punctuation():
    a = "OpenAI “rogue” agent activities found on Wikimedia projects"
    b = 'OpenAI "rogue" agent activities found on Wikimedia projects'
    assert normalize_title(a) == normalize_title(b)
    assert same_title(piece(1, title=a), piece(2, title=b, source="Medio B"))


def test_short_equal_titles_are_not_same_title():
    a = piece(1, title="Claude Haiku 5.5")
    b = piece(2, title="Claude Haiku 5.5", source="Medio B")
    assert same_title(a, b) is False


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (piece(1, url="https://x.com/a"), piece(2, url="https://x.com/a"), True),
        (piece(1, url="https://x.com/a"), piece(2, target_url="https://x.com/a"), True),
        (piece(1, target_url="https://x.com/a"), piece(2, target_url="https://x.com/a"), True),
        (piece(1), piece(2), False),
        (piece(1, url="https://x.com/a/"), piece(2, target_url="https://x.com/a#frag"), True),
    ],
    ids=["url", "target-url", "both-targets", "no-targets", "trailing-slash"],
)
def test_same_link_by_url_target_or_both_targets(a, b, expected):
    assert same_link(a, b) is expected


def test_pairs_skip_same_outlet():
    # Dos queries de HN son el mismo medio (outlet_key "hackernews").
    a = piece(1, platform=Platform.HACKERNEWS, source="HN · LLM", title=LONG_TITLE)
    b = piece(2, platform=Platform.HACKERNEWS, source="HN · OpenAI", title=LONG_TITLE)
    assert topic_pairs([a, b], [[0, 1]], vectors(1.0, 1.0)) == ([], [])


def test_shared_link_is_an_edge_not_a_candidate():
    a = piece(1, url="https://x.com/a", title=LONG_TITLE)
    b = piece(2, source="Medio B", target_url="https://x.com/a", title=LONG_TITLE)
    edges, candidates = topic_pairs([a, b], [[0, 1]], vectors(1.0, 1.0))
    assert edges == [ReplicaEdge(1, 2, ReplicaBasis.SAME_LINK)]
    assert candidates == []


def test_candidates_from_similarity_or_equal_title():
    first = piece(1)
    similar = piece(2, source="Medio B")
    distant = piece(3, source="Medio C")
    _, candidates = topic_pairs([first, similar], [[0, 1]], vectors(1.0, 0.71))
    assert [(c.a.item_id, c.b.item_id) for c in candidates] == [(1, 2)]
    assert topic_pairs([first, distant], [[0, 1]], vectors(1.0, 0.69)) == ([], [])

    titled = [piece(1, title=LONG_TITLE), piece(2, source="Medio B", title=LONG_TITLE)]
    _, candidates = topic_pairs(titled, [[0, 1]], vectors(1.0, 0.40))
    [pair] = candidates
    assert pair.same_title is True
    assert pair.similarity == pytest.approx(0.40)


def test_candidates_sorted_by_similarity_then_ids():
    # Similitudes con la pieza 1: 0.80 (pieza 2), 0.95 (pieza 3), 0.80 (pieza 4).
    # Entre 2, 3 y 4 los productos son mayores que 0.70 también: se ordena todo el conjunto.
    pieces = [piece(1), piece(2, source="B"), piece(3, source="C"), piece(4, source="D")]
    vecs = np.array([[1.0, 0.0], unit(0.80), unit(0.95), unit(0.80)])
    _, candidates = topic_pairs(pieces, [[0, 1, 2, 3]], vecs)
    sims = [c.similarity for c in candidates]
    assert sims == sorted(sims, reverse=True)
    ties = [(c.a.item_id, c.b.item_id) for c in candidates if c.similarity == pytest.approx(0.80)]
    assert ties == [(1, 2), (1, 4)]
    assert (candidates[0].a.item_id, candidates[0].b.item_id) == (2, 4)  # similitud 1.0


def test_pairs_never_cross_clusters():
    a = piece(1, title=LONG_TITLE)
    b = piece(2, source="Medio B", title=LONG_TITLE)
    assert topic_pairs([a, b], [[0], [1]], vectors(1.0, 1.0)) == ([], [])


def test_no_clusters_or_vectors_gives_nothing():
    assert topic_pairs([], [], np.empty((0, 2))) == ([], [])
    assert topic_pairs([piece(1), piece(2, source="B")], [], vectors(1.0, 1.0)) == ([], [])


def score_answer(score: float, confidence: float) -> dict:
    return {"type": "score", "score": score, "confidence": confidence}


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (None, None),
        (score_answer(3.0, 0.4), None),
        (score_answer(2.8, 0.9), True),
        (score_answer(2.4, 0.9), False),
        (score_answer(0.1, 0.9), False),
    ],
    ids=["missing", "low-confidence", "level-3", "level-2", "level-0"],
)
def test_verdict(answer, expected):
    assert same_story_verdict(answer) is expected


def pair(similarity: float, *, title: bool = False) -> CandidatePair:
    return CandidatePair(piece(1), piece(2, source="Medio B"), similarity, title)


@pytest.mark.parametrize(
    ("candidate", "verdict", "expected"),
    [
        (pair(0.75), True, ReplicaBasis.JEV),
        (pair(0.99, title=True), False, None),
        (pair(0.91), None, ReplicaBasis.SIMILARITY),
        (pair(0.5, title=True), None, ReplicaBasis.SAME_TITLE),
        (pair(0.85), None, None),
    ],
    ids=["jev-yes", "jev-no-beats-rule", "rule-similarity", "rule-title", "below-rule"],
)
def test_decide_pair(candidate, verdict, expected):
    assert decide_pair(candidate, verdict) is expected


def test_group_stories_picks_earliest_as_representative():
    pieces = [piece(1, hours_ago=5), piece(2, source="B", hours_ago=20)]
    stories = group_stories(pieces, [ReplicaEdge(1, 2, ReplicaBasis.JEV)])
    assert stories.representative_of == {1: 2}
    assert stories.replica_ids == frozenset({1})


def test_group_stories_ties_by_item_id():
    pieces = [piece(7, hours_ago=5), piece(3, source="B", hours_ago=5)]
    stories = group_stories(pieces, [ReplicaEdge(3, 7, ReplicaBasis.JEV)])
    assert stories.representative_of == {7: 3}


def test_group_stories_is_transitive():
    pieces = [piece(1, hours_ago=30), piece(2, source="B", hours_ago=20), piece(3, source="C")]
    edges = [ReplicaEdge(1, 2, ReplicaBasis.JEV), ReplicaEdge(2, 3, ReplicaBasis.JEV)]
    assert group_stories(pieces, edges).representative_of == {2: 1, 3: 1}


def test_all_pieces_replicas_of_one_story():
    pieces = [piece(i, source=f"Medio {i}", hours_ago=10 + i) for i in range(1, 6)]
    edges = [ReplicaEdge(1, i, ReplicaBasis.SAME_LINK) for i in range(2, 6)]
    stories = group_stories(pieces, edges)
    assert len(stories.replica_ids) == 4
    assert set(stories.representative_of.values()) == {5}  # la más antigua


def test_group_stories_without_edges_is_no_replicas():
    assert group_stories([piece(1), piece(2, source="B")], []) == NO_REPLICAS


def test_unverified_only_when_no_verified_edge():
    pieces = [piece(1, hours_ago=30), piece(2, source="B", hours_ago=20), piece(3, source="C")]
    # 1 —JEV— 2 —SIMILARITY— 3: la 2 tiene una arista verificada; la 3, ninguna.
    edges = [ReplicaEdge(1, 2, ReplicaBasis.JEV), ReplicaEdge(2, 3, ReplicaBasis.SIMILARITY)]
    assert group_stories(pieces, edges).unverified == frozenset({3})

    linked = [*edges, ReplicaEdge(1, 3, ReplicaBasis.SAME_LINK)]
    assert group_stories(pieces, linked).unverified == frozenset()

    only_rule = [ReplicaEdge(1, 2, ReplicaBasis.SAME_TITLE)]
    assert group_stories(pieces, only_rule).unverified == frozenset({2})


def test_replica_outlets_counts_distinct_outlets_other_than_representative():
    original = piece(1, source="Medio A", hours_ago=30)
    same_outlet_twice = [piece(2, source="Medio B"), piece(3, source="Medio B")]
    same_as_original = piece(4, source="Medio A")
    group = [original, *same_outlet_twice, same_as_original]
    edges = [ReplicaEdge(1, i, ReplicaBasis.JEV) for i in (2, 3, 4)]
    assert replica_outlets(group, group_stories(group, edges)) == {1: 1}


def test_replica_notes():
    assert replica_notes(0, unverified=False) == []
    [one] = replica_notes(1, unverified=False)
    assert one.startswith("1 pieza es una republicación")
    notes = replica_notes(3, unverified=True)
    assert len(notes) == 2
    assert notes[0].startswith("3 piezas son republicaciones")
    assert "sin verificar con Jev" in notes[1]
