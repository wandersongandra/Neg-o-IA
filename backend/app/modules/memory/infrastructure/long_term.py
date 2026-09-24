"""Persistência da memória longa em PostgreSQL/pgvector."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.embeddings import embed_text
from app.infrastructure.db import create_engine, create_session_factory
from app.modules.configuration.settings import get_settings
from app.modules.database.infrastructure import MemoryEntryORM, MemoryPolicyORM
from app.modules.memory.domain import LongTermMemoryEntry, MemoryPolicy, MemorySearchHit


def _user_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except ValueError as exc:
        raise ValueError("invalid user id") from exc


def _domain(row: MemoryEntryORM) -> LongTermMemoryEntry:
    return LongTermMemoryEntry(
        id=str(row.id),
        user_id=str(row.user_id),
        session_id=row.session_id,
        source=row.source,
        content=row.content,
        importance=float(row.importance),
        metadata=dict(row.attributes),
        created_at=row.created_at,
        expires_at=row.expires_at,
    )


class PostgresLongTermMemory:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._factory = session_factory or create_session_factory(
            create_engine(get_settings().database_url)
        )

    async def remember(
        self,
        user_id: str,
        content: str,
        *,
        session_id: str | None,
        source: str,
        importance: float,
        retention_days: int | None,
        metadata: dict[str, Any],
    ) -> LongTermMemoryEntry:
        parsed_user = _user_uuid(user_id)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        expires_at = (
            datetime.now(UTC) + timedelta(days=retention_days)
            if retention_days is not None
            else None
        )
        async with self._factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(MemoryEntryORM).where(
                        MemoryEntryORM.user_id == parsed_user,
                        MemoryEntryORM.content_hash == content_hash,
                        MemoryEntryORM.source == source,
                    )
                )
                row = result.scalar_one_or_none()
                if row is None:
                    row = MemoryEntryORM(
                        user_id=parsed_user,
                        session_id=session_id,
                        source=source,
                        content=content,
                        content_hash=content_hash,
                        importance=importance,
                        embedding=embed_text(content),
                        attributes=metadata,
                        expires_at=expires_at,
                    )
                    session.add(row)
                else:
                    row.session_id = session_id or row.session_id
                    row.importance = max(float(row.importance), importance)
                    row.expires_at = expires_at or row.expires_at
                    row.attributes = {**dict(row.attributes), **metadata}
                await session.flush()
                return _domain(row)

    async def search(self, user_id: str, query: str, *, limit: int) -> list[MemorySearchHit]:
        parsed_user = _user_uuid(user_id)
        query_embedding = embed_text(query)
        distance = cast(Any, MemoryEntryORM.embedding).cosine_distance(query_embedding)
        now = datetime.now(UTC)
        async with self._factory() as session:
            result = await session.execute(
                select(MemoryEntryORM, distance.label("distance"))
                .where(
                    MemoryEntryORM.user_id == parsed_user,
                    or_(MemoryEntryORM.expires_at.is_(None), MemoryEntryORM.expires_at > now),
                )
                .order_by(distance.asc(), MemoryEntryORM.importance.desc())
                .limit(limit)
            )
            hits: list[MemorySearchHit] = []
            for row, raw_distance in result.all():
                distance_value = float(raw_distance or 0.0)
                hits.append(
                    MemorySearchHit(
                        entry=_domain(row),
                        score=max(0.0, min(1.0, 1.0 - distance_value)),
                    )
                )
            return hits

    async def delete(self, user_id: str, memory_id: str) -> bool:
        parsed_user = _user_uuid(user_id)
        try:
            parsed_memory = uuid.UUID(memory_id)
        except ValueError:
            return False
        async with self._factory() as session:
            async with session.begin():
                row = await session.get(MemoryEntryORM, parsed_memory)
                if row is None or row.user_id != parsed_user:
                    return False
                await session.delete(row)
                return True

    async def get_policy(self, user_id: str) -> MemoryPolicy:
        parsed_user = _user_uuid(user_id)
        async with self._factory() as session:
            row = await session.get(MemoryPolicyORM, parsed_user)
            if row is None:
                return MemoryPolicy(
                    user_id=user_id,
                    auto_capture_enabled=False,
                    retention_days=90,
                )
            return MemoryPolicy(
                user_id=user_id,
                auto_capture_enabled=row.auto_capture_enabled,
                retention_days=row.retention_days,
            )

    async def set_policy(
        self,
        user_id: str,
        *,
        auto_capture_enabled: bool,
        retention_days: int,
    ) -> MemoryPolicy:
        parsed_user = _user_uuid(user_id)
        async with self._factory() as session:
            async with session.begin():
                row = await session.get(MemoryPolicyORM, parsed_user)
                if row is None:
                    row = MemoryPolicyORM(
                        user_id=parsed_user,
                        auto_capture_enabled=auto_capture_enabled,
                        retention_days=retention_days,
                    )
                    session.add(row)
                else:
                    row.auto_capture_enabled = auto_capture_enabled
                    row.retention_days = retention_days
                    row.updated_at = datetime.now(UTC)
                await session.flush()
        return MemoryPolicy(
            user_id=user_id,
            auto_capture_enabled=auto_capture_enabled,
            retention_days=retention_days,
        )
