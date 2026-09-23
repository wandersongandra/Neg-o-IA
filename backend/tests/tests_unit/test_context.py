"""Testes do contexto HTTP e sanitização de correlation IDs."""

from __future__ import annotations

from app.core.context import _safe_correlation_id


def test_safe_correlation_id_accepts_expected_charset() -> None:
    assert _safe_correlation_id("req-1234.abcd:child") == "req-1234.abcd:child"


def test_safe_correlation_id_rejects_control_characters() -> None:
    assert _safe_correlation_id("abc\nforged-log-line") is None


def test_safe_correlation_id_rejects_oversized_values() -> None:
    assert _safe_correlation_id("a" * 129) is None


def test_safe_correlation_id_trims_whitespace() -> None:
    assert _safe_correlation_id("  trace-123  ") == "trace-123"
