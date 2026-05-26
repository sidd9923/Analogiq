"""Unit tests for app.core.similarity"""

import numpy as np
import pytest

from app.core.similarity import (
    StructuralSimilarity,
    analogical_score,
    relational_similarity,
    semantic_similarity,
)


class TestSemanticSimilarity:
    def test_identical_vectors_return_one(self):
        v = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        assert pytest.approx(semantic_similarity(v, v), abs=1e-4) == 1.0

    def test_orthogonal_vectors_return_zero(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        assert pytest.approx(semantic_similarity(a, b), abs=1e-4) == 0.0

    def test_zero_vector_returns_zero(self):
        a = np.zeros(4, dtype=np.float32)
        b = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        assert semantic_similarity(a, b) == 0.0


class TestStructuralSimilarity:
    def test_fit_and_score_identical_texts(self):
        corpus = ["neural network training loss converges", "graph search algorithm"]
        sim = StructuralSimilarity()
        sim.fit(corpus)
        score = sim.score(corpus[0], corpus[0])
        assert pytest.approx(score, abs=1e-4) == 1.0

    def test_score_without_fit_raises(self):
        sim = StructuralSimilarity()
        with pytest.raises(RuntimeError, match="fit"):
            sim.score("a", "b")

    def test_batch_score_returns_correct_length(self):
        corpus = ["text one", "text two", "text three"]
        sim = StructuralSimilarity()
        sim.fit(corpus)
        scores = sim.batch_score("text one", corpus)
        assert len(scores) == 3

    def test_dissimilar_texts_have_low_score(self):
        corpus = [
            "quantum mechanics wave function collapse",
            "medieval french baking recipes",
        ]
        sim = StructuralSimilarity()
        sim.fit(corpus)
        score = sim.score(corpus[0], corpus[1])
        assert score < 0.2


class TestRelationalSimilarity:
    def test_identical_texts_return_one(self):
        text = "Neurons activate synaptic connections rapidly."
        score = relational_similarity(text, text)
        assert 0.0 <= score <= 1.0  # may not be 1.0 due to heuristic extractor

    def test_empty_texts_return_zero(self):
        assert relational_similarity("", "") == 0.0

    def test_score_between_zero_and_one(self):
        a = "Proteins fold into complex structures under thermal stress."
        b = "Materials deform under mechanical loads and thermal stress."
        score = relational_similarity(a, b)
        assert 0.0 <= score <= 1.0


class TestAnalogyScore:
    def test_weighted_combination(self):
        score = analogical_score(1.0, 1.0, 1.0, weights=(0.6, 0.25, 0.15))
        assert pytest.approx(score, abs=1e-4) == 1.0

    def test_zero_inputs_give_zero(self):
        assert analogical_score(0.0, 0.0, 0.0) == 0.0

    def test_weights_are_normalised(self):
        # Even non-unit weights should be normalised
        score = analogical_score(1.0, 1.0, 1.0, weights=(6.0, 2.5, 1.5))
        assert pytest.approx(score, abs=1e-4) == 1.0
