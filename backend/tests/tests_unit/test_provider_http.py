"""Tests for hardened external-provider HTTP handling."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.infrastructure.provider_http import (
    ProviderInvalidResponseError,
    ProviderResponseTooLargeError,
    new_provider_http_client,
    post_json_limited,
)


def test_provider_client_disables_redirects_and_ambient_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(
        "app.infrastructure.provider_http.httpx.AsyncClient",
        FakeClient,
    )

    new_provider_http_client(12.0)

    assert captured["follow_redirects"] is False
    assert captured["trust_env"] is False
    assert isinstance(captured["timeout"], httpx.Timeout)


@pytest.mark.asyncio
async def test_provider_response_rejects_declared_oversize() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            headers={"content-length": "1024"},
            content=b'{"ok": true}',
        )
    )
    async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
        with pytest.raises(ProviderResponseTooLargeError):
            await post_json_limited(
                client,
                "https://provider.example.test/v1",
                headers={},
                payload={"ping": "pong"},
                max_response_bytes=128,
            )


@pytest.mark.asyncio
async def test_provider_response_rejects_streamed_oversize() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=b"x" * 512)
    )
    async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
        with pytest.raises(ProviderResponseTooLargeError):
            await post_json_limited(
                client,
                "https://provider.example.test/v1",
                headers={},
                payload={"ping": "pong"},
                max_response_bytes=128,
            )


@pytest.mark.asyncio
async def test_provider_response_rejects_invalid_json() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=b"not-json")
    )
    async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
        with pytest.raises(ProviderInvalidResponseError):
            await post_json_limited(
                client,
                "https://provider.example.test/v1",
                headers={},
                payload={"ping": "pong"},
                max_response_bytes=1024,
            )


@pytest.mark.asyncio
async def test_provider_response_accepts_bounded_json_object() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json={"ok": True})
    )
    async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
        response = await post_json_limited(
            client,
            "https://provider.example.test/v1",
            headers={},
            payload={"ping": "pong"},
            max_response_bytes=1024,
        )

    assert response.status_code == 200
    assert response.payload == {"ok": True}
