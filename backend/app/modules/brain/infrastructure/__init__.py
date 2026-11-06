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

import httpx

from app.infrastructure.provider_http import (
    ProviderInvalidResponseError,
    ProviderResponseTooLargeError,
    new_provider_http_client,
    post_json_limited,
)
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

    async def run(self, operation: Callable[[], Awaitable[ModelResponse]]) -> ModelResponse:
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
            "cache_namespace": request.cache_namespace,
            "provider": request.provider,
            "model": request.model,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def _cache_get(cache_key: str) -> ModelResponse | None:
    try:
        from app.infrastructure.redis import get_redis

        client = get_redis()
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

        client = get_redis()
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


def _new_provider_http_client() -> Any:
    """Compatibilidade interna para testes e adapters do Brain."""
    return new_provider_http_client(60.0)


class NvidiaChatAdapter:
    """LLM via NVIDIA build.nvidia.com — endpoint OpenAI-compatível."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any | None = None

    def _http(self) -> Any:
        if self._client is None:
            self._client = _new_provider_http_client()
        return self._client

    async def complete(self, request: ModelRequest) -> ModelResponse:
        settings = self._settings
        started = time.perf_counter()
        payload = {
            "model": settings.brain_chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
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
            response = await post_json_limited(
                self._http(),
                f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
                payload=payload,
                max_response_bytes=settings.provider_max_response_bytes,
            )
        except ProviderResponseTooLargeError as exc:
            raise ProviderError("NVIDIA response exceeded configured limit") from exc
        except ProviderInvalidResponseError as exc:
            raise ProviderError("NVIDIA returned invalid JSON") from exc
        except Exception as exc:
            raise RetryableProviderError(f"erro de rede no NVIDIA: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code in {429, 500, 502, 503, 504, 529}:
            raise RetryableProviderError(f"NVIDIA HTTP {response.status_code}")
        if response.status_code != 200 or response.payload is None:
            raise ProviderError(f"NVIDIA HTTP {response.status_code}")
        try:
            data = response.payload
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
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
                f"EXTERNAL_AI_ENABLED=true e uma NVIDIA_API_KEY para ativar o "
                f"provedor externo. (eco: {user_text[:80]})"
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


async def _complete_chatgpt_plan(
    request: ModelRequest,
    *,
    settings: Settings,
) -> ModelResponse:
    from app.modules.brain.chatgpt_plan import ChatGPTPlanError, get_chatgpt_plan_store

    if not request.cache_namespace:
        raise ProviderError("ChatGPT plan requests require an authenticated user session")
    store = get_chatgpt_plan_store()
    try:
        token = await store.access_token(request.cache_namespace)
        model = request.model
        if not model:
            models = await store.models(request.cache_namespace)
            if not models:
                raise ChatGPTPlanError(
                    "A conta não retornou modelos disponíveis para Responses API."
                )
            model = models[0]["id"]
    except ChatGPTPlanError as exc:
        raise ProviderError(str(exc)) from exc

    instructions = "\n\n".join(
        message.content for message in request.messages if message.role == "system"
    )
    input_items = [
        {
            "type": "message",
            "role": message.role,
            "content": [{"type": "input_text", "text": message.content}],
        }
        for message in request.messages
        if message.role in {"user", "assistant"}
    ]
    payload: dict[str, Any] = {
        "model": model,
        "input": input_items,
        "store": False,
        "stream": True,
    }
    if instructions:
        payload["instructions"] = instructions

    started = time.perf_counter()
    output: list[str] = []
    response_size = 0
    usage: dict[str, int] | None = None
    client = new_provider_http_client(90.0)
    try:
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "text/event-stream",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as response:
            if response.status_code in {408, 429, 500, 502, 503, 504}:
                raise RetryableProviderError(
                    f"ChatGPT plan returned HTTP {response.status_code}"
                )
            if response.status_code != 200:
                raise ProviderError(
                    f"ChatGPT plan denied inference (HTTP {response.status_code})"
                )
            async for line in response.aiter_lines():
                response_size += len(line.encode("utf-8")) + 1
                if response_size > settings.provider_max_response_bytes:
                    raise ProviderError("ChatGPT plan stream exceeded configured response limit")
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw or raw == "[DONE]":
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ProviderError("ChatGPT plan returned malformed stream data") from exc
                if not isinstance(event, dict):
                    continue
                event_type = event.get("type")
                if event_type == "response.output_text.delta":
                    delta = event.get("delta")
                    if isinstance(delta, str):
                        output.append(delta)
                elif event_type in {"error", "response.failed"}:
                    error = event.get("error")
                    if isinstance(error, dict) and error.get("code") in {
                        "subscription_sharing_usage_unavailable",
                        "subscription_sharing_user_unavailable",
                    }:
                        raise RetryableProviderError("ChatGPT plan temporarily unavailable")
                    raise ProviderError("ChatGPT plan could not complete this request")
                elif event_type == "response.completed":
                    result = event.get("response")
                    if isinstance(result, dict) and isinstance(result.get("usage"), dict):
                        raw_usage = result["usage"]
                        usage = {
                            target: int(raw_usage[source])
                            for target, source in (
                                ("prompt_tokens", "input_tokens"),
                                ("completion_tokens", "output_tokens"),
                                ("total_tokens", "total_tokens"),
                            )
                            if isinstance(raw_usage.get(source), int)
                        }
    except httpx.TimeoutException as exc:
        raise RetryableProviderError("ChatGPT plan request timed out") from exc
    except httpx.HTTPError as exc:
        raise RetryableProviderError("ChatGPT plan network request failed") from exc
    finally:
        await client.aclose()

    text = "".join(output).strip()
    if not text:
        raise ProviderError("ChatGPT plan completed without a text response")
    return ModelResponse(
        text=text,
        model=model,
        latency_ms=int((time.perf_counter() - started) * 1000),
        usage=usage or None,
    )


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
        if request.provider == "chatgpt_plan":
            key = _cache_key(request)
            cached = await _cache_get(key)
            if cached is not None:
                return cached
            response = await _complete_chatgpt_plan(request, settings=settings)
            await _cache_set(key, response, settings.brain_cache_ttl_seconds)
            return response
        if request.provider == "nvidia" and (
            not settings.external_ai_enabled or not settings.nvidia_api_key
        ):
            raise ModelError("NVIDIA is not configured for this installation")
        if not settings.external_ai_enabled or not settings.nvidia_api_key:
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
                response = await self._retry_policy.run(lambda: adapter.complete(request))
                await self._primary_breaker.record_success()
                return response
            except RetryableProviderError as exc:
                _LOGGER.warning("primary_model_failed", extra={"error": str(exc)})
                await self._primary_breaker.record_failure()

        fallback_request = ModelRequest(
            messages=request.messages,
            task_type=request.task_type,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            cache_namespace=request.cache_namespace,
            provider=request.provider,
            model=request.model,
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
                _LOGGER.warning("fallback_model_failed", extra={"error": str(exc)})

        raise ModelError("todos os provedores de modelo falharam")

    async def _complete_fallback(self, request: ModelRequest) -> ModelResponse:
        settings = self._settings
        started = time.perf_counter()
        payload = {
            "model": settings.brain_fallback_model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
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
            async with _new_provider_http_client() as client:
                response = await post_json_limited(
                    client,
                    f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
                    payload=payload,
                    max_response_bytes=settings.provider_max_response_bytes,
                )
        except ProviderResponseTooLargeError as exc:
            raise ProviderError("fallback response exceeded configured limit") from exc
        except ProviderInvalidResponseError as exc:
            raise ProviderError("fallback returned invalid JSON") from exc
        except Exception as exc:
            raise RetryableProviderError(f"erro de rede no fallback: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code in {429, 500, 502, 503, 504, 529}:
            raise RetryableProviderError(f"fallback HTTP {response.status_code}")
        if response.status_code != 200 or response.payload is None:
            raise ProviderError(f"fallback HTTP {response.status_code}")
        try:
            data = response.payload
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
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
