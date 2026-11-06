"""Security-focused coverage for local Sign in with ChatGPT support."""

from __future__ import annotations

import uuid

import pytest

from app.modules.brain.chatgpt_plan import (
    ChatGPTPlanError,
    ChatGPTPlanStore,
    _valid_expires_in,
)
from app.modules.brain.siwc_client import SiwcError, _safe_api_url


def test_oauth_credential_ciphertext_is_bound_to_user_and_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ChatGPTPlanStore, "_key", staticmethod(lambda: b"k" * 32))
    user_id = uuid.uuid4()
    ciphertext = ChatGPTPlanStore._encrypt(user_id, "refresh", "refresh-secret-value")

    assert b"refresh-secret-value" not in ciphertext
    assert ChatGPTPlanStore._decrypt(user_id, "refresh", ciphertext) == "refresh-secret-value"
    with pytest.raises(ChatGPTPlanError):
        ChatGPTPlanStore._decrypt(uuid.uuid4(), "refresh", ciphertext)
    with pytest.raises(ChatGPTPlanError):
        ChatGPTPlanStore._decrypt(user_id, "access", ciphertext)


def test_oauth_credential_tampering_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ChatGPTPlanStore, "_key", staticmethod(lambda: b"k" * 32))
    user_id = uuid.uuid4()
    ciphertext = bytearray(ChatGPTPlanStore._encrypt(user_id, "access", "access-secret-value"))
    ciphertext[-1] ^= 1

    with pytest.raises(ChatGPTPlanError):
        ChatGPTPlanStore._decrypt(user_id, "access", bytes(ciphertext))


def test_refresh_token_lifetime_is_bounded() -> None:
    assert _valid_expires_in(60) == 60
    assert _valid_expires_in(86_400) == 86_400
    for value in (True, 0, 59, 86_401, "3600", None):
        with pytest.raises(ChatGPTPlanError):
            _valid_expires_in(value)


def test_cli_accepts_https_and_local_development_only() -> None:
    assert _safe_api_url("https://ultron.example.com/") == "https://ultron.example.com"
    assert _safe_api_url("http://127.0.0.1:3000") == "http://127.0.0.1:3000"
    assert _safe_api_url("http://[::1]:3000") == "http://[::1]:3000"
    for value in (
        "http://ultron.example.com",
        "https://user:secret@ultron.example.com",
        "https://ultron.example.com/api/v1",
        "https://ultron.example.com?token=secret",
    ):
        with pytest.raises(SiwcError):
            _safe_api_url(value)
