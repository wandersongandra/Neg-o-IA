"""Testes unitários da identidade centralizada da Sophie (Fase 1 — rebrand)."""

from __future__ import annotations

from app.modules.brain.identity import ASSISTANT_NAME, SYSTEM_PROMPT
from app.modules.brain.router import DEFAULT_CONFIG
from app.modules.conversation.application import (
    SYSTEM_PROMPT as CONVERSATION_SYSTEM_PROMPT,
)
from app.modules.security.application.identity import (
    hash_password,
    issue_session_token,
    verify_password,
)


def test_assistant_name_is_sophie() -> None:
    assert ASSISTANT_NAME == "Sophie"


def test_system_prompt_mentions_sophie_not_legacy_name() -> None:
    assert "Sophie" in SYSTEM_PROMPT
    assert "NEGÃO" not in SYSTEM_PROMPT
    assert "NEGAO" not in SYSTEM_PROMPT


def test_brain_default_config_uses_centralized_prompt() -> None:
    """Antes da Fase 1, brain/router.py tinha sua própria cópia do prompt —
    agora deve importar a mesma constante, eliminando o risco de divergência
    documentado em docs/sophie/CURRENT_STATE.md."""
    assert DEFAULT_CONFIG["system_prompt"] is SYSTEM_PROMPT


def test_conversation_uses_centralized_prompt() -> None:
    """Idem para conversation/application — este é o prompt realmente usado
    em cada turno de chat real (ver CURRENT_STATE.md §4)."""
    assert CONVERSATION_SYSTEM_PROMPT is SYSTEM_PROMPT


def test_password_hash_is_scrypt_and_not_reversible() -> None:
    encoded = hash_password("uma senha de teste suficientemente longa")
    assert encoded.startswith("scrypt$")
    assert encoded != "uma senha de teste suficientemente longa"
    assert verify_password("uma senha de teste suficientemente longa", encoded)
    assert not verify_password("senha incorreta", encoded)
    assert not verify_password("uma senha de teste suficientemente longa", encoded[:-1] + "x")


def test_session_token_uses_opaque_csprng_value() -> None:
    first = issue_session_token()
    second = issue_session_token()
    assert len(first) >= 64
    assert first != second
    assert "$" not in first
