"""Contratos do módulo conversation — domain (framework-free).

Responsabilidade: sessões de conversa retomáveis com histórico limitado,
persona do NEGÃO e contexto para o Brain. Não chama LLM diretamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

_VALID_ROLES = frozenset({"system", "user", "assistant"})


@dataclass(frozen=True)
class ConversationMessage:
    """Uma mensagem do histórico da conversa."""

    role: str
    content: str
    created_at: str

    def __post_init__(self) -> None:
        if self.role not in _VALID_ROLES:
            raise ValueError(f"role inválido: {self.role!r}")
        if not self.content.strip():
            raise ValueError("mensagem vazia")


@dataclass(frozen=True)
class ConversationSession:
    """Metadados de uma sessão de conversa."""

    session_id: str
    user_id: str | None
    created_at: str
    updated_at: str
    message_count: int
    name: str | None = None


class ConversationStorePort(Protocol):
    """Porta de persistência do histórico de conversas."""

    async def start_session(self, user_id: str | None) -> ConversationSession: ...

    async def append_message(
        self, session_id: str, role: str, content: str
    ) -> ConversationMessage: ...

    async def get_messages(self, session_id: str) -> list[ConversationMessage]: ...

    async def list_sessions(self) -> list[ConversationSession]: ...

    async def rename_session(self, session_id: str, name: str | None) -> bool: ...

    async def delete_session(self, session_id: str) -> bool: ...


__all__ = [
    "ConversationMessage",
    "ConversationSession",
    "ConversationStorePort",
]
