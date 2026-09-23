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
