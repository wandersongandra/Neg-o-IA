"""Adaptadores do módulo brain — provedores de LLM, resiliência e roteamento.

- `NvidiaChatAdapter`: LLM via NVIDIA build.nvidia.com (OpenAI-compatível).
- `MockLLMAdapter`: respostas locais (sem chave de API ou em testes).
- `CircuitBreaker`, `RetryPolicy` e cache em Redis dão resiliência ao router.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.modules.brain.domain import (
    ModelRequest,
    ModelResponse,
)
from app.modules.configuration.settings import Settings, get_settings

_LOGGER = logging.getLogger("app.modules.brain.infrastructure")


class BrainError(Exception):
    """Erro base do módulo brain."""


class RetryableProviderError(BrainError):
    """Falha transitória (timeout, 5xx, 429) — pode ser repetida."""


class ProviderError(BrainError):
    """Falha definitiva do provedor (4xx, payload inválido)."""


class ModelError(BrainError):
    """Todos os provedores/modelos falharam."""


class CircuitBreaker:
    """Interruptor de circuito: fecha após falhas consecutivas e esfria."""

    def __init__(
        self,
        *,
        failures_threshold: int = 3,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self._failures_threshold = max(1, failures_threshold)
        self._cooldown_seconds = cooldown_seconds
        self._failures = 0
        self._opened_at: float | None = None
        self._half_open_trial = False
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        async with self._lock:
            if self._opened_at is None:
                return True
            if time.monotonic() - self._opened_at >= self._cooldown_seconds:
                self._half_open_trial = True
                return True
            return False

    async def record_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._opened_at = None
            self._half_open_trial = False

    async def record_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._half_open_trial:
                self._opened_at = time.monotonic()
                self._half_open_trial = False
            elif self._failures >= self._failures_threshold:
                self._opened_at = time.monotonic()
                self._failures = 0


class RetryPolicy:
    """Repete chamadas transitórias com backoff exponencial."""

    def __init__(self, *, attempts: int = 2, base_delay_seconds: float = 0.5) -> None:
        self._attempts = max(0, attempts)
        self._base_delay = base_delay_seconds

    async def run(
        self, operation: Callable[[], Awaitable[ModelResponse]]
    ) -> ModelResponse:
        last_error: Exception | None = None
        for attempt in range(self._attempts + 1):
            try:
                return await operation()
            except RetryableProviderError as exc:
                last_error = exc
                if attempt < self._attempts:
                    delay = min(3.0, self._base_delay * (2**attempt))
                    _LOGGER.warning(
                        "retry_provider",
                        extra={
                            "attempt": attempt + 1,
                            "delay_seconds": delay,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(delay)
            except ProviderError:
                raise
        raise RetryableProviderError(
            f"provedor falhou após {self._attempts + 1} tentativas: {last_error}"
        )


def _cache_key(request: ModelRequest) -> str:
    payload = json.dumps(
        {
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "task_type": request.task_type.value,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def _cache_get(cache_key: str) -> ModelResponse | None:
    try:
        from app.infrastructure.redis import get_redis

        client = await get_redis()
        raw = await client.get(f"brain:cache:{cache_key}")
        if not raw:
            return None
        data = json.loads(raw)
        return ModelResponse(
            text=data["text"],
            model=data["model"],
            latency_ms=0,
            usage=data.get("usage"),
            cached=True,
            fallback_used=data.get("fallback_used", False),
        )
    except Exception:
        return None


async def _cache_set(cache_key: str, response: ModelResponse, ttl: int) -> None:
    try:
        from app.infrastructure.redis import get_redis

        client = await get_redis()
        payload = json.dumps(
            {
                "text": response.text,
                "model": response.model,
                "usage": response.usage,
                "fallback_used": response.fallback_used,
            }
        )
        await client.set(f"brain:cache:{cache_key}", payload, ex=ttl)
    except Exception:
        _LOGGER.debug("cache_write_skipped", exc_info=True)


class NvidiaChatAdapter:
    """LLM via NVIDIA build.nvidia.com — endpoint OpenAI-compatível."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any | None = None

    def _http(self) -> Any:
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def complete(self, request: ModelRequest) -> ModelResponse:
        settings = self._settings
        started = time.perf_counter()
        payload = {
            "model": settings.brain_chat_model,
            "messages": [
                {"role": m.role, "content": m.content} for m in request.messages
            ],
            "temperature": (
                request.temperature
                if request.temperature is not None
                else settings.brain_temperature
            ),
            "max_tokens": (
                request.max_tokens if request.max_tokens is not None else settings.brain_max_tokens
            ),
        }
        try:
            response = await self._http().post(
                f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
            )
        except Exception as exc:
            raise RetryableProviderError(f"erro de rede no NVIDIA: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code in {429, 500, 502, 503, 504}:
            raise RetryableProviderError(
                f"NVIDIA {response.status_code}: {response.text[:200]}"
            )
        if response.status_code != 200:
            raise ProviderError(
                f"NVIDIA {response.status_code}: {response.text[:200]}"
            )
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage")
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderError(f"NVIDIA payload inválido: {exc}") from exc
        return ModelResponse(
            text=text,
            model=settings.brain_chat_model,
            latency_ms=latency_ms,
            usage={k: int(v) for k, v in usage.items()} if usage else None,
        )


class MockLLMAdapter:
    """Resposta local quando não há chave de API (e para testes)."""

    async def complete(self, request: ModelRequest) -> ModelResponse:
        await asyncio.sleep(0.001)
        user_text = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        return ModelResponse(
            text=(
                f"Opa, chefe! Meu cérebro está em modo local — configure "
                f"NEGAO_NVIDIA_API_KEY para ativar o GPT-OSS-120B. "
                f"(eco: {user_text[:80]})"
            ),
            model="local-mock",
            latency_ms=1,
            usage=None,
        )


_nvidia_adapter: NvidiaChatAdapter | None = None
_mock_adapter: MockLLMAdapter | None = None


def _get_nvidia_adapter(settings: Settings) -> NvidiaChatAdapter:
    global _nvidia_adapter
    if _nvidia_adapter is None:
        _nvidia_adapter = NvidiaChatAdapter(settings)
    return _nvidia_adapter


def _get_mock_adapter() -> MockLLMAdapter:
    global _mock_adapter
    if _mock_adapter is None:
        _mock_adapter = MockLLMAdapter()
    return _mock_adapter


class ModelRouter:
    """Roteia a requisição: primário → fallback, com resiliência e cache."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._primary_breaker = CircuitBreaker(
            failures_threshold=settings.brain_circuit_failures,
            cooldown_seconds=settings.brain_circuit_cooldown_seconds,
        )
        self._fallback_breaker = CircuitBreaker(
            failures_threshold=settings.brain_circuit_failures,
            cooldown_seconds=settings.brain_circuit_cooldown_seconds,
        )
        self._retry_policy = RetryPolicy(attempts=settings.brain_retry_attempts)

    async def complete(self, request: ModelRequest) -> ModelResponse:
        settings = self._settings
        if not settings.nvidia_api_key:
            return await _get_mock_adapter().complete(request)

        key = _cache_key(request)
        cached = await _cache_get(key)
        if cached is not None:
            return cached

        response = await self._complete_with_resilience(request)
        await _cache_set(key, response, settings.brain_cache_ttl_seconds)
        return response

    async def _complete_with_resilience(self, request: ModelRequest) -> ModelResponse:
        settings = self._settings
        adapter = _get_nvidia_adapter(settings)
        if await self._primary_breaker.can_execute():
            try:
                response = await self._retry_policy.run(
                    lambda: adapter.complete(request)
                )
                await self._primary_breaker.record_success()
                return response
            except RetryableProviderError as exc:
                _LOGGER.warning(
                    "primary_model_failed", extra={"error": str(exc)}
                )
                await self._primary_breaker.record_failure()

        fallback_request = ModelRequest(
            messages=request.messages,
            task_type=request.task_type,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        if await self._fallback_breaker.can_execute():
            try:
                response = await self._retry_policy.run(
                    lambda: self._complete_fallback(fallback_request)
                )
                await self._fallback_breaker.record_success()
                return response
            except RetryableProviderError as exc:
                await self._fallback_breaker.record_failure()
                _LOGGER.warning(
                    "fallback_model_failed", extra={"error": str(exc)}
                )

        raise ModelError("todos os provedores de modelo falharam")

    async def _complete_fallback(self, request: ModelRequest) -> ModelResponse:
        import httpx

        settings = self._settings
        started = time.perf_counter()
        payload = {
            "model": settings.brain_fallback_model,
            "messages": [
                {"role": m.role, "content": m.content} for m in request.messages
            ],
            "temperature": (
                request.temperature
                if request.temperature is not None
                else settings.brain_temperature
            ),
            "max_tokens": (
                request.max_tokens if request.max_tokens is not None else settings.brain_max_tokens
            ),
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
                )
        except Exception as exc:
            raise RetryableProviderError(f"erro de rede no fallback: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code in {429, 500, 502, 503, 504}:
            raise RetryableProviderError(
                f"fallback {response.status_code}: {response.text[:200]}"
            )
        if response.status_code != 200:
            raise ProviderError(f"fallback {response.status_code}: {response.text[:200]}")
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage")
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderError(f"fallback payload inválido: {exc}") from exc
        return ModelResponse(
            text=text,
            model=settings.brain_fallback_model,
            latency_ms=latency_ms,
            usage={k: int(v) for k, v in usage.items()} if usage else None,
            fallback_used=True,
        )


_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    """Singleton do ModelRouter (config da primeira chamada)."""
    global _router
    if _router is None:
        _router = ModelRouter(get_settings())
    return _router


def reset_router() -> None:
    """Reset dos singletons (uso em testes)."""
    global _router, _nvidia_adapter
    _router = None
    _nvidia_adapter = None
