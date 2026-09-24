"""Persistência do Knowledge Vault em PostgreSQL/pgvector."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.embeddings import embed_text
from app.infrastructure.db import create_engine, create_session_factory
from app.modules.configuration.settings import get_settings
from app.modules.database.infrastructure import KnowledgeChunkORM, KnowledgeDocumentORM
from app.modules.knowledge.domain import KnowledgeDocument, KnowledgeSearchHit

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120


def chunk_text(
    content: str,
    *,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("invalid chunk settings")
    normalized = " ".join(content.split())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + size)
        if end < len(normalized):
            split = normalized.rfind(" ", start, end)
            if split > start + size // 2:
                end = split
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _user_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except ValueError as exc:
        raise ValueError("invalid user id") from exc


class PostgresKnowledgeStore:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._factory = session_factory or create_session_factory(
            create_engine(get_settings().database_url)
        )

    async def ingest(
        self,
        user_id: str,
        *,
        title: str,
        content: str,
        source_type: str,
        source_uri: str | None,
    ) -> KnowledgeDocument:
        parsed_user = _user_uuid(user_id)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        chunks = chunk_text(content)
        async with self._factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(KnowledgeDocumentORM).where(
                        KnowledgeDocumentORM.user_id == parsed_user,
                        KnowledgeDocumentORM.content_hash == content_hash,
                    )
                )
                existing = result.scalar_one_or_none()
                if existing is not None:
                    count_result = await session.execute(
                        select(func.count())
                        .select_from(KnowledgeChunkORM)
                        .where(KnowledgeChunkORM.document_id == existing.id)
                    )
                    return KnowledgeDocument(
                        id=str(existing.id),
                        user_id=user_id,
                        title=existing.title,
                        source_type=existing.source_type,
                        source_uri=existing.source_uri,
                        chunk_count=int(count_result.scalar_one()),
                        created_at=existing.created_at,
                        updated_at=existing.updated_at,
                    )

                document = KnowledgeDocumentORM(
                    user_id=parsed_user,
                    title=title,
                    source_type=source_type,
                    source_uri=source_uri,
                    content_hash=content_hash,
                )
                session.add(document)
                await session.flush()
                for index, chunk in enumerate(chunks):
                    session.add(
                        KnowledgeChunkORM(
                            document_id=document.id,
                            user_id=parsed_user,
                            chunk_index=index,
                            content=chunk,
                            embedding=embed_text(chunk),
                            attributes={"title": title, "source_type": source_type},
                        )
                    )
                await session.flush()
                return KnowledgeDocument(
                    id=str(document.id),
                    user_id=user_id,
                    title=document.title,
                    source_type=document.source_type,
                    source_uri=document.source_uri,
                    chunk_count=len(chunks),
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                )

    async def search(
        self,
        user_id: str,
        query: str,
        *,
        limit: int,
    ) -> list[KnowledgeSearchHit]:
        parsed_user = _user_uuid(user_id)
        query_embedding = embed_text(query)
        distance = cast(Any, KnowledgeChunkORM.embedding).cosine_distance(query_embedding)
        async with self._factory() as session:
            result = await session.execute(
                select(KnowledgeChunkORM, KnowledgeDocumentORM, distance.label("distance"))
                .join(
                    KnowledgeDocumentORM,
                    KnowledgeDocumentORM.id == KnowledgeChunkORM.document_id,
                )
                .where(KnowledgeChunkORM.user_id == parsed_user)
                .order_by(distance.asc())
                .limit(limit)
            )
            return [
                KnowledgeSearchHit(
                    document_id=str(document.id),
                    chunk_id=str(chunk.id),
                    title=document.title,
                    source_type=document.source_type,
                    source_uri=document.source_uri,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=max(0.0, min(1.0, 1.0 - float(raw_distance or 0.0))),
                )
                for chunk, document, raw_distance in result.all()
            ]

    async def list_documents(self, user_id: str) -> list[KnowledgeDocument]:
        parsed_user = _user_uuid(user_id)
        async with self._factory() as session:
            rows = await session.execute(
                select(
                    KnowledgeDocumentORM,
                    func.count(KnowledgeChunkORM.id).label("chunk_count"),
                )
                .outerjoin(
                    KnowledgeChunkORM,
                    KnowledgeChunkORM.document_id == KnowledgeDocumentORM.id,
                )
                .where(KnowledgeDocumentORM.user_id == parsed_user)
                .group_by(KnowledgeDocumentORM.id)
                .order_by(KnowledgeDocumentORM.updated_at.desc())
            )
            return [
                KnowledgeDocument(
                    id=str(document.id),
                    user_id=user_id,
                    title=document.title,
                    source_type=document.source_type,
                    source_uri=document.source_uri,
                    chunk_count=int(chunk_count),
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                )
                for document, chunk_count in rows.all()
            ]

    async def delete_document(self, user_id: str, document_id: str) -> bool:
        parsed_user = _user_uuid(user_id)
        try:
            parsed_document = uuid.UUID(document_id)
        except ValueError:
            return False
        async with self._factory() as session:
            async with session.begin():
                row = await session.get(KnowledgeDocumentORM, parsed_document)
                if row is None or row.user_id != parsed_user:
                    return False
                await session.delete(row)
                return True
