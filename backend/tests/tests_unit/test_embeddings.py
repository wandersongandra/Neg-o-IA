"""Testes do embedding local e determinístico."""

from __future__ import annotations

import math

from app.core.embeddings import EMBEDDING_DIMENSIONS, cosine_similarity, embed_text


def test_embedding_is_deterministic_and_normalized() -> None:
    first = embed_text("Sophie lembra projetos e preferências")
    second = embed_text("Sophie lembra projetos e preferências")

    assert first == second
    assert len(first) == EMBEDDING_DIMENSIONS
    norm = math.sqrt(sum(value * value for value in first))
    assert abs(norm - 1.0) < 1e-6


def test_related_text_scores_above_unrelated_text() -> None:
    query = embed_text("projeto de software em Python")
    related = embed_text("software Python para um projeto")
    unrelated = embed_text("banana oceano bicicleta")

    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


def test_empty_text_still_has_stable_embedding() -> None:
    vector = embed_text("")
    assert len(vector) == EMBEDDING_DIMENSIONS
    assert any(value != 0 for value in vector)
