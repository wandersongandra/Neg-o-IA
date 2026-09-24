"""Embeddings locais determinísticos para memória/RAG.

Não usa rede nem envia conteúdo para terceiros. É um baseline de feature
hashing que mantém o pipeline funcional até um provider de embeddings ser
configurado explicitamente.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

EMBEDDING_DIMENSIONS = 384
_TOKEN_RE = re.compile(r"[\wÀ-ÿ]{2,}", re.UNICODE)


def _features(text: str) -> list[str]:
    tokens = [token.casefold() for token in _TOKEN_RE.findall(text)]
    if not tokens:
        return ["__empty__"]
    bigrams = [f"{a}::{b}" for a, b in zip(tokens, tokens[1:], strict=False)]
    return [*tokens, *bigrams]


def embed_text(text: str, *, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    """Gera vetor unitário determinístico usando feature hashing."""
    if dimensions <= 0:
        raise ValueError("embedding dimensions must be positive")
    vector = [0.0] * dimensions
    counts = Counter(_features(text))
    for feature, count in counts.items():
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        weight = 1.0 + math.log(float(count))
        vector[index] += sign * weight
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimensions")
    return sum(a * b for a, b in zip(left, right, strict=True))
