"""Contratos do módulo brain — domain (framework-free).

O Brain é o núcleo de inteligência único do NEGÃO AI: recebe mensagens,
roteia para o modelo de linguagem (com retry, circuit breaker, fallback e
cache) e entrega a resposta. Não faz I/O externa nem conhece outros módulos.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

_VALID_ROLES = frozenset({"system", "user", "assistant"})


class TaskType(StrEnum):
    """Tipo da tarefa — base para heurísticas de roteamento de modelo."""

    CHAT = "chat"
    SUMMARY = "summary"
    VOICE = "voice"
    EXTRACTION = "extraction"


@dataclass(frozen=True)
class ChatMessage:
    """Uma mensagem do diálogo (contrato OpenAI-compatível)."""

    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in _VALID_ROLES:
            raise ValueError(f"role inválido: {self.role!r}")
        if not self.content.strip():
            raise ValueError("mensagem vazia")


@dataclass(frozen=True)
class ModelRequest:
    """Pedido completo para o Model Router."""

    messages: list[ChatMessage]
    task_type: TaskType = TaskType.CHAT
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ModelResponse:
    """Resposta do Model Router."""

    text: str
    model: str
    latency_ms: int
    usage: dict[str, int] | None = None
    cached: bool = False
    fallback_used: bool = False


class LLMAdapter(Protocol):
    """Um provedor de LLM (NVIDIA, OpenAI, mock…)."""

    async def complete(self, request: ModelRequest) -> ModelResponse: ...


class BrainPort(Protocol):
    """Porta pública do Brain (consumida por Conversation/Voice/Vision)."""

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        task_type: TaskType = TaskType.CHAT,
        session_id: str | None = None,
        user_id: str | None = None,
        trace_id: str | None = None,
    ) -> ModelResponse: ...

    async def process_input(
        self,
        text: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]: ...


__all__ = [
    "BrainPort",
    "ChatMessage",
    "LLMAdapter",
    "ModelRequest",
    "ModelResponse",
    "TaskType",
]
