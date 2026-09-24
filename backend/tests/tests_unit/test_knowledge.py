"""Testes puros do chunking do Knowledge Vault."""

from __future__ import annotations

import pytest

from app.modules.knowledge.infrastructure import chunk_text


def test_chunk_text_keeps_all_content_in_order() -> None:
    text = " ".join(f"palavra{i}" for i in range(300))
    chunks = chunk_text(text, size=240, overlap=40)

    assert len(chunks) > 1
    assert all(chunks)
    assert chunks[0].startswith("palavra0")
    assert "palavra299" in chunks[-1]


def test_chunk_text_normalizes_whitespace() -> None:
    assert chunk_text("  um\n\ntexto   curto  ", size=100, overlap=10) == ["um texto curto"]


def test_chunk_text_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", size=10, overlap=10)
