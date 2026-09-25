"""HTTP client hardened for external AI providers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx


class ProviderResponseTooLargeError(RuntimeError):
    """Provider response exceeded the configured memory budget."""


class ProviderInvalidResponseError(RuntimeError):
    """Provider response was not a valid JSON object."""


@dataclass(frozen=True, slots=True)
class ProviderHttpResponse:
    status_code: int
    payload: dict[str, Any] | None


def new_provider_http_client(timeout_seconds: float = 60.0) -> httpx.AsyncClient:
    """Build a provider client that ignores ambient proxies and redirects."""
    connect_timeout = min(10.0, max(1.0, timeout_seconds))
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds, connect=connect_timeout),
        follow_redirects=False,
        trust_env=False,
        limits=httpx.Limits(
            max_connections=20,
            max_keepalive_connections=10,
            keepalive_expiry=30.0,
        ),
    )


async def read_json_limited(
    response: httpx.Response,
    *,
    max_response_bytes: int,
) -> ProviderHttpResponse:
    """Cap a streamed provider response before parsing it into Python objects."""
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError:
            declared_length = -1
        if declared_length > max_response_bytes:
            raise ProviderResponseTooLargeError("provider response exceeds configured limit")

    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > max_response_bytes:
            raise ProviderResponseTooLargeError("provider response exceeds configured limit")
        chunks.append(chunk)

    if response.status_code >= 400:
        return ProviderHttpResponse(status_code=response.status_code, payload=None)

    raw = b"".join(chunks)
    try:
        decoded = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderInvalidResponseError("provider returned invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise ProviderInvalidResponseError("provider returned invalid JSON payload")
    return ProviderHttpResponse(status_code=response.status_code, payload=decoded)


async def post_json_limited(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    max_response_bytes: int,
) -> ProviderHttpResponse:
    """POST JSON and cap the response body before parsing it into Python objects."""
    async with client.stream("POST", url, headers=headers, json=payload) as response:
        return await read_json_limited(response, max_response_bytes=max_response_bytes)
