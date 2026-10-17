"""Republicaciones de la misma nota dentro de un tema (CLAUDE.md §7, "Cross-source").

Una republicación es una copia, traducción o reenvío de la misma pieza en otro medio. Dos medios
que cuentan por separado el mismo hecho no lo son: eso es validación cruzada. Puro: los veredictos
de Jev llegan ya leídos y la DB la toca `services.replicas`.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations
from typing import TYPE_CHECKING, Any

import numpy as np

from app.intelligence.cross_source import outlet_key

if TYPE_CHECKING:
    # Solo para tipos: `opportunities` importa este módulo y un import real sería circular.
    from app.intelligence.opportunities import Piece

# Calibración del 18/10 con datos reales (.claude/plans/intel-dedup-replicas.plan.md): por debajo
# de 0.90 el coseno mezcla republicaciones con coberturas independientes; desde 0.70 decide Jev.
JEV_MIN_SIMILARITY = 0.70
FALLBACK_MIN_SIMILARITY = 0.90  # precisión 8/8 en la muestra real
MIN_TITLE_WORDS = 5  # con 4 entra "Claude Haiku 5.5", que es ambiguo
SAME_STORY_LEVEL = 3  # "la misma nota replicada" en pair.v1.yaml
SAME_STORY_MIN_CONFIDENCE = 0.5  # docs/jev.md, "Del juicio a la decisión"

REPLICAS_UNVERIFIED_NOTE = (
    "Algunas republicaciones se detectaron por título o similitud de texto, sin verificar con Jev."
)


class ReplicaBasis(StrEnum):
    SAME_LINK = "same_link"
    SAME_TITLE = "same_title"
    JEV = "jev"
    SIMILARITY = "similarity"


VERIFIED_BASES = {ReplicaBasis.SAME_LINK, ReplicaBasis.JEV}


def normalize_title(title: str) -> str:
    # Comillas tipográficas y guiones cambiaban entre copias reales del mismo título.
    text = unicodedata.normalize("NFKC", title).casefold()
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def same_title(a: Piece, b: Piece) -> bool:
    title = normalize_title(a.title)
    return title == normalize_title(b.title) and len(title.split()) >= MIN_TITLE_WORDS


def _link(url: str) -> str:
    return url.split("#", 1)[0].rstrip("/")


def same_link(a: Piece, b: Piece) -> bool:
    a_links = {_link(a.url)} | ({_link(a.target_url)} if a.target_url else set())
    b_links = {_link(b.url)} | ({_link(b.target_url)} if b.target_url else set())
    return bool(a_links & b_links)


@dataclass(frozen=True)
class CandidatePair:
    a: Piece  # item_id menor
    b: Piece
    similarity: float
    same_title: bool


@dataclass(frozen=True)
class ReplicaEdge:
    a: int
    b: int
    basis: ReplicaBasis


def _outlet(p: Piece) -> str:
    return outlet_key(p.platform.value, p.source_name)


def _cluster_pairs(
    pieces: Sequence[Piece], members: Sequence[int], vectors: np.ndarray
) -> tuple[list[ReplicaEdge], list[CandidatePair]]:
    edges, candidates = [], []
    for i, j in combinations(members, 2):
        a, b = sorted((pieces[i], pieces[j]), key=lambda p: p.item_id)
        # Un medio ya cuenta una vez: dentro del mismo no hay nada que deduplicar.
        if _outlet(a) == _outlet(b):
            continue
        if same_link(a, b):
            edges.append(ReplicaEdge(a.item_id, b.item_id, ReplicaBasis.SAME_LINK))
            continue
        similarity, title = float(vectors[i] @ vectors[j]), same_title(a, b)
        if similarity >= JEV_MIN_SIMILARITY or title:
            candidates.append(CandidatePair(a, b, similarity, title))
    return edges, candidates


def topic_pairs(
    pieces: Sequence[Piece], clusters: Sequence[Sequence[int]], vectors: np.ndarray
) -> tuple[list[ReplicaEdge], list[CandidatePair]]:
    """Aristas por enlace compartido y candidatos a Jev, dentro de cada cluster y entre medios
    distintos. `vectors` normalizados, uno por pieza. Candidatos por similitud descendente y,
    en empate, por ids."""
    edges: list[ReplicaEdge] = []
    candidates: list[CandidatePair] = []
    if len(vectors) == 0:
        return edges, candidates
    for members in clusters:
        cluster_edges, cluster_candidates = _cluster_pairs(pieces, members, vectors)
        edges += cluster_edges
        candidates += cluster_candidates
    candidates.sort(key=lambda c: (-c.similarity, c.a.item_id, c.b.item_id))
    return edges, candidates


def same_story_verdict(answer: Mapping[str, Any] | None) -> bool | None:
    # `score` es una media ponderada: se redondea al nivel. El nivel 2 ("mismo acontecimiento
    # contado por separado") es cobertura independiente, así que es un "no", no un "incierto".
    if answer is None or answer.get("score") is None or answer.get("confidence") is None:
        return None
    if answer["confidence"] < SAME_STORY_MIN_CONFIDENCE:
        return None
    return round(answer["score"]) >= SAME_STORY_LEVEL


def decide_pair(pair: CandidatePair, verdict: bool | None) -> ReplicaBasis | None:
    if verdict is not None:
        return ReplicaBasis.JEV if verdict else None
    if pair.same_title:
        return ReplicaBasis.SAME_TITLE
    if pair.similarity >= FALLBACK_MIN_SIMILARITY:
        return ReplicaBasis.SIMILARITY
    return None


@dataclass(frozen=True)
class StoryAssignment:
    representative_of: Mapping[int, int]  # republicación → representante (solo republicaciones)
    # Republicaciones que no llegan a su representante solo por aristas SAME_LINK o JEV.
    unverified: frozenset[int]

    @property
    def replica_ids(self) -> frozenset[int]:
        return frozenset(self.representative_of)


NO_REPLICAS = StoryAssignment({}, frozenset())


def _components(edges: Iterable[ReplicaEdge]) -> list[list[int]]:
    parent: dict[int, int] = {}

    def find(x: int) -> int:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in edges:
        parent[find(e.a)] = find(e.b)
    groups: dict[int, list[int]] = defaultdict(list)
    for x in parent:
        groups[find(x)].append(x)
    return list(groups.values())


def _story_index(edges: Iterable[ReplicaEdge]) -> dict[int, int]:
    return {i: k for k, members in enumerate(_components(edges)) for i in members}


def _without_contradicted_rules(
    edges: Sequence[ReplicaEdge], independent: Collection[tuple[int, int]]
) -> list[ReplicaEdge]:
    # Un "no" seguro de Jev manda sobre la regla (D2), también cuando la regla une el par a
    # través de otras piezas: en esa nota se quitan las aristas de regla. Las cadenas de solo
    # aristas verificadas siguen el riesgo aceptado de D5.
    if not independent:
        return list(edges)
    story_of = _story_index(edges)
    contradicted = {
        story_of[a] for a, b in independent if a in story_of and story_of.get(b) == story_of[a]
    }
    return [e for e in edges if e.basis in VERIFIED_BASES or story_of[e.a] not in contradicted]


def group_stories(
    pieces: Sequence[Piece],
    edges: Sequence[ReplicaEdge],
    *,
    independent: Collection[tuple[int, int]] = (),  # "no" seguro de Jev
) -> StoryAssignment:
    edges = _without_contradicted_rules(edges, independent)
    if not edges:
        return NO_REPLICAS
    by_id = {p.item_id: p for p in pieces}
    representative_of: dict[int, int] = {}
    for members in _components(edges):
        # Lo primero publicado suele ser el original.
        rep = min(members, key=lambda i: (by_id[i].published_at, i))
        representative_of.update({i: rep for i in members if i != rep})
    return StoryAssignment(representative_of, _unverified(representative_of, edges))


def _unverified(
    representative_of: Mapping[int, int], edges: Sequence[ReplicaEdge]
) -> frozenset[int]:
    # Por vínculo con la representante, no por pieza: una arista de Jev con otra copia no
    # verifica una copia unida a la representante solo por la regla.
    story_of = _story_index(e for e in edges if e.basis in VERIFIED_BASES)
    return frozenset(
        i
        for i, rep in representative_of.items()
        if i not in story_of or story_of.get(rep) != story_of[i]
    )


def replica_outlets(group: Sequence[Piece], stories: StoryAssignment) -> dict[int, int]:
    """Por representante del grupo: medios distintos del suyo que republican su nota."""
    by_id = {p.item_id: p for p in group}
    outlets: dict[int, set[str]] = defaultdict(set)
    for item_id, rep in stories.representative_of.items():
        if item_id in by_id and rep in by_id:
            outlets[rep].add(_outlet(by_id[item_id]))
    return {rep: len(keys - {_outlet(by_id[rep])}) for rep, keys in outlets.items()}


def replica_notes(replicas: int, *, unverified: bool) -> list[str]:
    if replicas == 0:
        return []
    if replicas == 1:
        count = "1 pieza es una republicación de la misma nota"
    else:
        count = f"{replicas} piezas son republicaciones de la misma nota"
    notes = [f"{count}: no cuentan como fuentes independientes ni para la saturación."]
    if unverified:
        notes.append(REPLICAS_UNVERIFIED_NOTE)
    return notes
