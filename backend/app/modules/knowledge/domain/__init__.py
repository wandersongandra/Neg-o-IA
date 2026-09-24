"""Contratos do Knowledge Vault — domain (framework-free)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    id: str
    user_id: str
    title: str
    source_type: str
    source_uri: str | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeSearchHit:
    document_id: str
    chunk_id: str
    title: str
    source_type: str
    source_uri: str | None
    chunk_index: int
    content: str
    score: float


class KnowledgePort(Protocol):
    async def search(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 5,
    ) -> list[KnowledgeSearchHit]: ...
