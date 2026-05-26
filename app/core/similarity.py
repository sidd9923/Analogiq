"""
Analogical similarity algorithms used by the search pipeline.

Three complementary signals are computed and combined:
  1. Semantic similarity   — cosine distance over sentence embeddings
  2. Structural similarity — TF-IDF + Jaccard over abstract n-gram profiles
  3. Relational similarity — overlap of relational predicates (SVO triples)

A weighted ensemble (configurable via settings) fuses the three scores into a
final analogical score in [0, 1].

References
----------
* Gentner, D. (1983). Structure-mapping: A theoretical framework for analogy.
* Hope et al. (2017). Accelerating Innovation Through Analogy Mining (KDD).
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config.settings import settings


# ---------------------------------------------------------------------------
# 1. Semantic similarity (cosine over dense vectors)
# ---------------------------------------------------------------------------

def semantic_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Cosine similarity between two L2-normalised sentence embeddings."""
    a = vec_a.flatten()
    b = vec_b.flatten()
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / norm)


# ---------------------------------------------------------------------------
# 2. Structural similarity (TF-IDF Jaccard on unigram/bigram profiles)
# ---------------------------------------------------------------------------

class StructuralSimilarity:
    """
    Computes TF-IDF cosine similarity between abstract text pairs.
    Fit once on the corpus, then call `score(a, b)` at query time.
    """

    def __init__(self, ngram_range: tuple[int, int] = (1, 2), max_features: int = 20_000):
        self._vectorizer = TfidfVectorizer(
            ngram_range=ngram_range,
            max_features=max_features,
            sublinear_tf=True,
            stop_words="english",
        )
        self._fitted = False

    def fit(self, corpus: list[str]) -> "StructuralSimilarity":
        self._vectorizer.fit(corpus)
        self._fitted = True
        return self

    def score(self, text_a: str, text_b: str) -> float:
        if not self._fitted:
            raise RuntimeError("StructuralSimilarity must be fit on corpus before scoring.")
        vecs = self._vectorizer.transform([text_a, text_b])
        return float(cosine_similarity(vecs[0], vecs[1])[0, 0])

    def batch_score(self, query: str, candidates: list[str]) -> np.ndarray:
        """Return an array of scores for one query against N candidates."""
        if not self._fitted:
            raise RuntimeError("StructuralSimilarity must be fit on corpus before scoring.")
        docs = [query] + candidates
        matrix = self._vectorizer.transform(docs)
        return cosine_similarity(matrix[0:1], matrix[1:])[0]


# ---------------------------------------------------------------------------
# 3. Relational similarity (lightweight SVO triple Jaccard)
# ---------------------------------------------------------------------------

_SVO_PATTERN = re.compile(
    r"(?P<subj>[A-Z][a-z]+(?:\s[A-Z][a-z]+)*)"
    r"\s+(?P<verb>[a-z]+(?:es|ed|ing)?)"
    r"\s+(?P<obj>[a-z]+(?:\s[a-z]+)?)",
    re.MULTILINE,
)


def _extract_triples(text: str) -> set[tuple[str, str, str]]:
    """
    Heuristic extraction of (subject, verb, object) triples from text.
    This is intentionally lightweight; a production system would use SpaCy/OpenIE.
    """
    triples = set()
    for m in _SVO_PATTERN.finditer(text):
        triples.add((m.group("subj").lower(), m.group("verb").lower(), m.group("obj").lower()))
    return triples


def relational_similarity(text_a: str, text_b: str) -> float:
    """
    Jaccard similarity over extracted SVO triples.
    Returns a value in [0, 1]; 0 if both sets are empty.
    """
    triples_a = _extract_triples(text_a)
    triples_b = _extract_triples(text_b)

    if not triples_a and not triples_b:
        return 0.0

    intersection = triples_a & triples_b
    union = triples_a | triples_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# 4. Ensemble combiner
# ---------------------------------------------------------------------------

def analogical_score(
    semantic: float,
    structural: float,
    relational: float,
    weights: Optional[tuple[float, float, float]] = None,
) -> float:
    """
    Weighted linear combination of the three similarity signals.

    Default weights are read from settings:
        ANALOGY_WEIGHT_SEMANTIC    (default 0.6)
        ANALOGY_WEIGHT_STRUCTURAL  (default 0.25)
        ANALOGY_WEIGHT_RELATIONAL  (default 0.15)
    """
    if weights is None:
        w_sem = settings.ANALOGY_WEIGHT_SEMANTIC
        w_str = settings.ANALOGY_WEIGHT_STRUCTURAL
        w_rel = settings.ANALOGY_WEIGHT_RELATIONAL
    else:
        w_sem, w_str, w_rel = weights

    total = w_sem + w_str + w_rel
    return (w_sem * semantic + w_str * structural + w_rel * relational) / total
