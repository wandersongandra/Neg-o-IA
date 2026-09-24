"""Contratos do módulo memory — domain (framework-free)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ShortTermMemoryEntry:
    user_id: str
    session_id: str
    key: str
    value: Any
    ttl_seconds: int
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class MemoryRecallResult:
    entries: tuple[ShortTermMemoryEntry, ...]
    score: float


@dataclass(frozen=True, slots=True)
class LongTermMemoryEntry:
    id: str
    user_id: str
    session_id: str | None
    source: str
    content: str
    importance: float
    metadata: dict[str, Any]
    created_at: datetime
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class MemorySearchHit:
    entry: LongTermMemoryEntry
    score: float


@dataclass(frozen=True, slots=True)
class MemoryPolicy:
    user_id: str
    auto_capture_enabled: bool
    retention_days: int
