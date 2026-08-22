"""Testes unitários do alias de variáveis de ambiente NEGAO_* -> SOPHIE_*
(Fase 1 — rebrand seguro, ver docs/sophie/COMPATIBILITY.md)."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from app.modules.configuration.settings import _apply_legacy_env_aliases

_PROBE_FIELDS = ("SOPHIE_TTS_RATE", "NEGAO_TTS_RATE", "SOPHIE_APP_NAME", "NEGAO_APP_NAME")


@pytest.fixture(autouse=True)
def _cleanup_env() -> Iterator[None]:
    yield
    for var in _PROBE_FIELDS:
        os.environ.pop(var, None)


def test_sophie_var_populates_legacy_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEGAO_TTS_RATE", raising=False)
    monkeypatch.setenv("SOPHIE_TTS_RATE", "+10%")
    _apply_legacy_env_aliases()
    assert os.environ["NEGAO_TTS_RATE"] == "+10%"


def test_legacy_var_alone_is_preserved_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem SOPHIE_*, o comportamento atual (deploys existentes usando só
    NEGAO_*) não muda em nada."""
    monkeypatch.delenv("SOPHIE_APP_NAME", raising=False)
    monkeypatch.setenv("NEGAO_APP_NAME", "Legacy Name")
    _apply_legacy_env_aliases()
    assert os.environ["NEGAO_APP_NAME"] == "Legacy Name"
    assert "SOPHIE_APP_NAME" not in os.environ


def test_sophie_var_takes_precedence_over_existing_legacy_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SOPHIE_* deve vencer quando NEGAO_* também está definida."""
    monkeypatch.setenv("NEGAO_TTS_RATE", "+0%")
    monkeypatch.setenv("SOPHIE_TTS_RATE", "+99%")
    _apply_legacy_env_aliases()
    assert os.environ["NEGAO_TTS_RATE"] == "+99%"


def test_neither_var_set_is_a_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOPHIE_TTS_RATE", raising=False)
    monkeypatch.delenv("NEGAO_TTS_RATE", raising=False)
    _apply_legacy_env_aliases()
    assert "NEGAO_TTS_RATE" not in os.environ
    assert "SOPHIE_TTS_RATE" not in os.environ
