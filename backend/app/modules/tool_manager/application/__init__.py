"""Tool Manager V1 — ferramentas internas allowlisted, auditadas e limitadas."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.infrastructure.db import check_database_health
from app.infrastructure.redis import check_redis_health, get_redis
from app.modules.configuration.settings import get_settings
from app.modules.events.envelope import build_envelope
from app.modules.tool_manager.domain import ToolExecutionResult, ToolSpec

_LOGGER = logging.getLogger("app.modules.tool_manager.application")
PRODUCER = "tool_manager"
_service: ToolManagerService | None = None

ToolHandler = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class ToolNotFoundError(LookupError):
    pass


class ToolConfirmationRequiredError(PermissionError):
    pass


class ToolCircuitOpenError(RuntimeError):
    pass


@dataclass(slots=True)
class _CircuitState:
    failures: int = 0
    open_until: float = 0.0


def _string_arg(arguments: dict[str, Any], name: str, *, max_length: int = 4000) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"{name} must be a non-empty string up to {max_length} chars")
    return value.strip()


def _int_arg(
    arguments: dict[str, Any],
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = arguments.get(name, default)
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


class ToolManagerService:
    def __init__(self) -> None:
        settings = get_settings()
        self._semaphore = asyncio.Semaphore(settings.tool_max_concurrency)
        self._circuits: dict[str, _CircuitState] = {}
        self._specs = self._build_specs()
        self._handlers: dict[str, ToolHandler] = {
            "memory.search": self._memory_search,
            "memory.remember": self._memory_remember,
            "knowledge.search": self._knowledge_search,
            "knowledge.list_documents": self._knowledge_list,
            "system.health": self._system_health,
        }

    @staticmethod
    def _build_specs() -> dict[str, ToolSpec]:
        return {
            "memory.search": ToolSpec(
                name="memory.search",
                description="Busca somente leitura na memória longa do usuário.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "maxLength": 1000},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                risk="read",
                requires_confirmation=False,
                automation_safe=True,
            ),
            "memory.remember": ToolSpec(
                name="memory.remember",
                description="Grava uma memória explícita do usuário.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "maxLength": 4000},
                        "importance": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["content"],
                    "additionalProperties": False,
                },
                risk="write",
                requires_confirmation=True,
                automation_safe=False,
            ),
            "knowledge.search": ToolSpec(
                name="knowledge.search",
                description="Busca somente leitura no Knowledge Vault do usuário.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "maxLength": 1000},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                risk="read",
                requires_confirmation=False,
                automation_safe=True,
            ),
            "knowledge.list_documents": ToolSpec(
                name="knowledge.list_documents",
                description="Lista documentos do Knowledge Vault.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                risk="read",
                requires_confirmation=False,
                automation_safe=True,
            ),
            "system.health": ToolSpec(
                name="system.health",
                description="Consulta saúde de PostgreSQL e Redis sem alterar estado.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                risk="read",
                requires_confirmation=False,
                automation_safe=True,
            ),
        }

    def catalog(self) -> list[ToolSpec]:
        return [self._specs[name] for name in sorted(self._specs)]

    def get_spec(self, tool_name: str) -> ToolSpec | None:
        return self._specs.get(tool_name)

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        user_id: str,
        confirmed: bool = False,
        idempotency_key: str | None = None,
    ) -> ToolExecutionResult:
        spec = self._specs.get(tool_name)
        handler = self._handlers.get(tool_name)
        if spec is None or handler is None:
            raise ToolNotFoundError(tool_name)
        if spec.requires_confirmation and not confirmed:
            raise ToolConfirmationRequiredError(tool_name)

        cached = await self._idempotency_get(user_id, tool_name, idempotency_key)
        if cached is not None:
            return ToolExecutionResult(tool_name=tool_name, output=cached, cached=True)

        state = self._circuits.setdefault(tool_name, _CircuitState())
        now = time.monotonic()
        if state.open_until > now:
            raise ToolCircuitOpenError(tool_name)

        settings = get_settings()
        try:
            async with self._semaphore:
                async with asyncio.timeout(settings.tool_timeout_seconds):
                    output = await handler(user_id, dict(arguments))
        except Exception:
            state.failures += 1
            if state.failures >= settings.tool_circuit_failures:
                state.open_until = time.monotonic() + settings.tool_circuit_cooldown_seconds
                state.failures = 0
            await self._publish(
                "tool.execution.failed",
                user_id,
                tool_name,
                {"argument_keys": sorted(arguments)},
            )
            raise

        state.failures = 0
        state.open_until = 0.0
        await self._idempotency_set(user_id, tool_name, idempotency_key, output)
        await self._publish(
            "tool.execution.completed",
            user_id,
            tool_name,
            {"argument_keys": sorted(arguments)},
        )
        return ToolExecutionResult(tool_name=tool_name, output=output)

    async def _memory_search(self, user_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        from app.modules.memory.application.long_term import get_long_term_memory_service

        query = _string_arg(arguments, "query", max_length=1000)
        limit = _int_arg(arguments, "limit", default=5, minimum=1, maximum=10)
        hits = await get_long_term_memory_service().search(user_id, query, limit=limit)
        return {
            "hits": [
                {
                    "id": hit.entry.id,
                    "content": hit.entry.content,
                    "source": hit.entry.source,
                    "score": hit.score,
                }
                for hit in hits
            ]
        }

    async def _memory_remember(self, user_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        from app.modules.memory.application.long_term import get_long_term_memory_service

        content = _string_arg(arguments, "content", max_length=4000)
        importance_raw = arguments.get("importance", 0.7)
        if not isinstance(importance_raw, (int, float)) or isinstance(importance_raw, bool):
            raise ValueError("importance must be numeric")
        importance = float(importance_raw)
        if not 0 <= importance <= 1:
            raise ValueError("importance must be between 0 and 1")
        entry = await get_long_term_memory_service().remember(
            user_id,
            content,
            source="explicit_tool",
            importance=importance,
        )
        return {"id": entry.id, "stored": True}

    async def _knowledge_search(self, user_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        from app.modules.knowledge.application import get_knowledge_service

        query = _string_arg(arguments, "query", max_length=1000)
        limit = _int_arg(arguments, "limit", default=5, minimum=1, maximum=10)
        hits = await get_knowledge_service().search(user_id, query, limit=limit)
        return {
            "hits": [
                {
                    "document_id": hit.document_id,
                    "title": hit.title,
                    "content": hit.content,
                    "score": hit.score,
                }
                for hit in hits
            ]
        }

    async def _knowledge_list(self, user_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if arguments:
            raise ValueError("knowledge.list_documents does not accept arguments")
        from app.modules.knowledge.application import get_knowledge_service

        docs = await get_knowledge_service().list_documents(user_id)
        return {
            "documents": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "source_type": doc.source_type,
                    "chunk_count": doc.chunk_count,
                }
                for doc in docs
            ]
        }

    async def _system_health(self, user_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        del user_id
        if arguments:
            raise ValueError("system.health does not accept arguments")
        database_ok, redis_ok = await asyncio.gather(
            check_database_health(),
            check_redis_health(),
        )
        return {
            "database": "ok" if database_ok else "degraded",
            "redis": "ok" if redis_ok else "degraded",
            "ready": database_ok and redis_ok,
        }

    @staticmethod
    def _idempotency_cache_key(
        user_id: str,
        tool_name: str,
        idempotency_key: str,
    ) -> str:
        digest = hashlib.sha256(
            f"{user_id}:{tool_name}:{idempotency_key}".encode()
        ).hexdigest()
        return f"tool:idem:{digest}"

    async def _idempotency_get(
        self,
        user_id: str,
        tool_name: str,
        idempotency_key: str | None,
    ) -> dict[str, Any] | None:
        if not idempotency_key:
            return None
        try:
            raw = await get_redis().get(
                self._idempotency_cache_key(user_id, tool_name, idempotency_key)
            )
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            return dict(data)
        except Exception:
            _LOGGER.warning("tool_idempotency_read_failed", exc_info=True)
            return None

    async def _idempotency_set(
        self,
        user_id: str,
        tool_name: str,
        idempotency_key: str | None,
        output: dict[str, Any],
    ) -> None:
        if not idempotency_key:
            return
        try:
            await get_redis().set(
                self._idempotency_cache_key(user_id, tool_name, idempotency_key),
                json.dumps(output, ensure_ascii=False, default=str),
                ex=86_400,
                nx=True,
            )
        except Exception:
            _LOGGER.warning("tool_idempotency_write_failed", exc_info=True)

    async def _publish(
        self,
        event_type: str,
        user_id: str,
        tool_name: str,
        payload: dict[str, Any],
    ) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    event_type,
                    PRODUCER,
                    {"tool_name": tool_name, **payload},
                    user_id=user_id,
                )
            )
        except Exception:
            _LOGGER.warning("tool_event_publish_failed", exc_info=True)


def get_tool_manager_service() -> ToolManagerService:
    global _service
    if _service is None:
        _service = ToolManagerService()
    return _service
