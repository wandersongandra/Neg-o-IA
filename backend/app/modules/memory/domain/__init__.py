"""Contratos do módulo memory — domain (framework-free).

A memória de curto prazo é sempre isolada por usuário e por sessão.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ShortTermMemoryEntry:
    """Entrada de memória de curto prazo (STM) de um usuário/sessão."""

    user_id: str
    session_id: str
    key: str
    value: Any
    ttl_seconds: int
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class MemoryRecallResult:
    """Resultado de um recall de memória."""

    entries: tuple[ShortTermMemoryEntry, ...]
    score: float


@dataclass(frozen=True, slots=True)
class LongTermMemoryEntry:
    """Memória persistente explicitamente autorizada pelo usuário."""

    id: str
    user_id: str
    content: str
    kind: str
    importance: int
    source_session_id: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime | None
    expires_at: datetime | None
    score: float | None = None
