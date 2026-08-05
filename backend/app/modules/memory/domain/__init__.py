"""Contratos do módulo memory — domain (framework-free).

v0: memória de curto prazo (STM) em Redis. Longo prazo/vetorial chegam em v1.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ShortTermMemoryEntry:
    """Entrada de memória de curto prazo (STM) de uma sessão."""

    session_id: str
    key: str
    value: Any
    ttl_seconds: int
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class MemoryRecallResult:
    """Resultado de um recall de memória (v0: score 1.0 se houver entradas)."""

    entries: tuple[ShortTermMemoryEntry, ...]
    score: float
