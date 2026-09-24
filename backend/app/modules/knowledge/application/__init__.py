"""Knowledge Vault — ingestão de texto e busca local com pgvector."""

from __future__ import annotations

import logging
from typing import Any

from app.modules.events.envelope import build_envelope
from app.modules.knowledge.domain import KnowledgeDocument, KnowledgeSearchHit
from app.modules.knowledge.infrastructure import PostgresKnowledgeStore

_LOGGER = logging.getLogger("app.modules.knowledge.application")
PRODUCER = "knowledge"
_service: KnowledgeService | None = None


class KnowledgeService:
    def __init__(self, store: PostgresKnowledgeStore | None = None) -> None:
        self._store = store or PostgresKnowledgeStore()

    async def ingest(
        self,
        user_id: str,
        *,
        title: str,
        content: str,
        source_type: str = "manual",
        source_uri: str | None = None,
    ) -> KnowledgeDocument:
        normalized_title = title.strip()
        normalized_content = content.strip()
        if not normalized_title or len(normalized_title) > 256:
            raise ValueError("title must contain 1..256 characters")
        if not normalized_content or len(normalized_content) > 200_000:
            raise ValueError("content must contain 1..200000 characters")
        document = await self._store.ingest(
            user_id,
            title=normalized_title,
            content=normalized_content,
            source_type=source_type,
            source_uri=source_uri,
        )
        await self._publish(
            "knowledge.document.ingested",
            {"user_id": user_id, "document_id": document.id, "chunks": document.chunk_count},
        )
        return document

    async def search(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 5,
    ) -> list[KnowledgeSearchHit]:
        if not query.strip():
            return []
        hits = await self._store.search(user_id, query.strip(), limit=max(1, min(limit, 10)))
        await self._publish(
            "knowledge.lookup.completed",
            {"user_id": user_id, "hits": len(hits)},
        )
        return hits

    async def list_documents(self, user_id: str) -> list[KnowledgeDocument]:
        return await self._store.list_documents(user_id)

    async def delete_document(self, user_id: str, document_id: str) -> bool:
        removed = await self._store.delete_document(user_id, document_id)
        if removed:
            await self._publish(
                "knowledge.document.deleted",
                {"user_id": user_id, "document_id": document_id},
            )
        return removed

    async def build_context(self, user_id: str, query: str, *, limit: int = 5) -> str:
        hits = await self.search(user_id, query, limit=limit)
        return "\n".join(
            f"- [{hit.title}; trecho {hit.chunk_index}; score={hit.score:.2f}] {hit.content}"
            for hit in hits
        )

    async def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    event_type,
                    PRODUCER,
                    payload,
                    user_id=payload.get("user_id"),
                )
            )
        except Exception as exc:
            _LOGGER.warning(
                "knowledge_event_failed",
                extra={"event_type": event_type, "error": str(exc)},
            )


def get_knowledge_service() -> KnowledgeService:
    global _service
    if _service is None:
        _service = KnowledgeService()
    return _service
