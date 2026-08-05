"""Testes unitários do módulo brain — router, resiliência e eventos."""

from __future__ import annotations

from types import MethodType
from typing import Any

import pytest
from fakeredis import FakeAsyncRedis

from app.modules.brain.application import get_brain_service, reset_brain_service
from app.modules.brain.domain import ChatMessage, ModelRequest, ModelResponse, TaskType
from app.modules.brain.infrastructure import (
    CircuitBreaker,
    ModelError,
    ModelRouter,
    NvidiaChatAdapter,
    ProviderError,
    RetryableProviderError,
    RetryPolicy,
    get_model_router,
    reset_router,
)
from app.modules.configuration.settings import get_settings
from app.modules.events.envelope import EventEnvelope


class FlakyAdapter:
    """Adapter de teste: falha N vezes, depois responde."""

    def __init__(self, failures_before_success: int = 1) -> None:
        self._remaining = failures_before_success
        self.calls = 0
        self.retryable = True

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        if self._remaining > 0:
            self._remaining -= 1
            if self.retryable:
                raise RetryableProviderError("transitório")
            raise ProviderError("definitivo")
        return ModelResponse(text="ok", model="test", latency_ms=1)


class FailingAdapter:
    async def complete(self, request: ModelRequest) -> ModelResponse:
        raise RetryableProviderError("sempre falha")


class OkAdapter:
    async def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(text="sucesso", model="test", latency_ms=1)


def _request() -> ModelRequest:
    return ModelRequest(messages=[ChatMessage(role="user", content="oi")])


async def test_retry_policy_retries_transient_then_succeeds() -> None:
    policy = RetryPolicy(attempts=2, base_delay_seconds=0)
    adapter = FlakyAdapter(failures_before_success=1)
    response = await policy.run(lambda: adapter.complete(_request()))
    assert response.text == "ok"
    assert adapter.calls == 2


async def test_retry_policy_gives_up_after_attempts() -> None:
    policy = RetryPolicy(attempts=1, base_delay_seconds=0)
    adapter = FlakyAdapter(failures_before_success=99)
    with pytest.raises(RetryableProviderError):
        await policy.run(lambda: adapter.complete(_request()))
    assert adapter.calls == 2


async def test_retry_policy_does_not_retry_definitive_error() -> None:
    policy = RetryPolicy(attempts=2, base_delay_seconds=0)
    adapter = FlakyAdapter(failures_before_success=1)
    adapter.retryable = False
    with pytest.raises(ProviderError):
        await policy.run(lambda: adapter.complete(_request()))
    assert adapter.calls == 1


async def test_circuit_breaker_opens_after_failures() -> None:
    breaker = CircuitBreaker(failures_threshold=2, cooldown_seconds=3600)
    assert await breaker.can_execute()
    await breaker.record_failure()
    assert await breaker.can_execute()
    await breaker.record_failure()
    assert not await breaker.can_execute()


async def test_circuit_breaker_half_open_allows_trial_and_closes_on_success() -> None:
    breaker = CircuitBreaker(failures_threshold=2, cooldown_seconds=60)
    await breaker.record_failure()
    await breaker.record_failure()
    assert not await breaker.can_execute()
    assert breaker._opened_at is not None
    breaker._opened_at -= 61
    assert await breaker.can_execute()
    await breaker.record_success()
    assert await breaker.can_execute()


async def test_router_falls_back_when_primary_fails(monkeypatch: Any) -> None:
    monkeypatch.setattr(get_settings(), "nvidia_api_key", "test-key")

    class FailingPrimary:
        async def complete(self, request: ModelRequest) -> ModelResponse:
            raise RetryableProviderError("primário fora")

    async def fake_fallback(_request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            text="fallback ok",
            model=get_settings().brain_fallback_model,
            latency_ms=1,
            fallback_used=True,
        )

    router = ModelRouter(get_settings())
    router._primary_breaker = CircuitBreaker(failures_threshold=1, cooldown_seconds=0)
    router._fallback_breaker = CircuitBreaker(failures_threshold=1, cooldown_seconds=0)
    router._retry_policy = RetryPolicy(attempts=0, base_delay_seconds=0)
    monkeypatch.setattr(router, "_complete_fallback", fake_fallback)
    monkeypatch.setattr(NvidiaChatAdapter, "complete", FailingPrimary.complete)
    try:
        response = await router.complete(_request())
    finally:
        reset_router()
    assert response.fallback_used
    assert response.text == "fallback ok"


async def test_router_raises_when_all_providers_fail(monkeypatch: Any) -> None:
    monkeypatch.setattr(get_settings(), "nvidia_api_key", "test-key")

    async def failing(self: Any, _request: ModelRequest) -> ModelResponse:
        raise RetryableProviderError("fora")

    router = ModelRouter(get_settings())
    router._primary_breaker = CircuitBreaker(failures_threshold=1, cooldown_seconds=0)
    router._fallback_breaker = CircuitBreaker(failures_threshold=1, cooldown_seconds=0)
    router._retry_policy = RetryPolicy(attempts=0, base_delay_seconds=0)
    monkeypatch.setattr(router, "_complete_fallback", MethodType(failing, router))
    monkeypatch.setattr(NvidiaChatAdapter, "complete", failing)
    try:
        with pytest.raises(ModelError):
            await router.complete(_request())
    finally:
        reset_router()


async def test_mock_adapter_used_without_key(monkeypatch: Any) -> None:
    monkeypatch.setattr(get_settings(), "nvidia_api_key", "")
    reset_router()
    try:
        response = await get_model_router().complete(_request())
    finally:
        reset_router()
    assert response.model == "local-mock"
    assert "NEGAO_NVIDIA_API_KEY" in response.text


async def test_cache_hit_skips_second_call(monkeypatch: Any) -> None:
    monkeypatch.setattr(get_settings(), "nvidia_api_key", "test-key")
    fake_redis = FakeAsyncRedis()

    async def _get_redis() -> FakeAsyncRedis:
        return fake_redis

    monkeypatch.setattr("app.infrastructure.redis.get_redis", _get_redis)

    class CountingAdapter:
        calls = 0

        async def complete(self, request: ModelRequest) -> ModelResponse:
            CountingAdapter.calls += 1
            return ModelResponse(text="cacheável", model="test", latency_ms=1)

    router = ModelRouter(get_settings())
    monkeypatch.setattr(router, "_complete_with_resilience", CountingAdapter().complete)
    try:
        first = await router.complete(_request())
        second = await router.complete(_request())
    finally:
        reset_router()
    assert first.cached is False
    assert second.cached is True
    assert CountingAdapter.calls == 1


async def test_brain_service_publishes_events(monkeypatch: Any) -> None:
    published: list[EventEnvelope] = []

    class FakeBus:
        async def publish_event(self, envelope: EventEnvelope) -> None:
            published.append(envelope)

    monkeypatch.setattr(
        "app.modules.events.application.get_event_bus_service", lambda: FakeBus()
    )
    monkeypatch.setattr(get_settings(), "nvidia_api_key", "")
    reset_router()
    reset_brain_service()
    try:
        service = get_brain_service()
        response = await service.complete(
            [ChatMessage(role="user", content="teste")], task_type=TaskType.CHAT
        )
    finally:
        reset_brain_service()
        reset_router()
    assert response.text
    assert response.model == "local-mock"
    types = {e.type for e in published}
    assert "brain.request.started" in types
    assert "brain.request.completed" in types


async def test_process_input_returns_dict(monkeypatch: Any) -> None:
    monkeypatch.setattr(get_settings(), "nvidia_api_key", "")
    reset_router()
    reset_brain_service()
    try:
        service = get_brain_service()
        result = await service.process_input("oi chefe")
    finally:
        reset_brain_service()
        reset_router()
    assert isinstance(result, dict)
    assert "text" in result
    assert "model" in result
