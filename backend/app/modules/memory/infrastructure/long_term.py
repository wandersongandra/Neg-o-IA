"""Persistent long-term memory backed by PostgreSQL.

All operations require the authenticated user's canonical UUID and include it
in every read/update/delete predicate. User-controlled content is never used to
build SQL strings.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.infrastructure.db import create_engine, create_session_factory
from app.modules.configuration.settings import get_settings
from app.modules.memory.domain import LongTermMemoryEntry

_ALLOWED_KINDS = frozenset({"note", "preference", "fact", "instruction"})
_MAX_CONTENT_LENGTH = 4000
_MAX_METADATA_BYTES = 8 * 1024


class LongTermMemoryPersistenceError(RuntimeError):
    """Persistent memory storage is unavailable or returned invalid data."""


def _validate_content(content: str) -> str:
    normalized = content.strip()
    if not normalized or len(normalized) > _MAX_CONTENT_LENGTH:
        raise ValueError("memory content must contain between 1 and 4000 characters")
    return normalized


def _validate_kind(kind: str) -> str:
    normalized = kind.strip().lower()
    if normalized not in _ALLOWED_KINDS:
        raise ValueError("invalid memory kind")
    return normalized


def _validate_importance(importance: int) -> int:
    if not 1 <= importance <= 5:
        raise ValueError("memory importance must be between 1 and 5")
    return importance


def _metadata_json(metadata: dict[str, Any] | None) -> str:
    payload = json.dumps(metadata or {}, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(payload.encode("utf-8")) > _MAX_METADATA_BYTES:
        raise ValueError("memory metadata is too large")
    return payload


def _entry_from_mapping(mapping: Any, *, score: float | None = None) -> LongTermMemoryEntry:
    metadata = mapping["metadata"]
    if not isinstance(metadata, dict):
        metadata = {}
    return LongTermMemoryEntry(
        id=str(mapping["id"]),
        user_id=str(mapping["user_id"]),
        content=str(mapping["content"]),
        kind=str(mapping["kind"]),
        importance=int(mapping["importance"]),
        source_session_id=(
            str(mapping["source_session_id"]) if mapping["source_session_id"] is not None else None
        ),
        metadata=metadata,
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
        last_accessed_at=mapping["last_accessed_at"],
        expires_at=mapping["expires_at"],
        score=score,
    )


class PostgresLongTermMemory:
    """User-isolated durable memory store."""

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or get_settings().database_url

    def _session_factory(self) -> Any:
        return create_session_factory(create_engine(self._database_url))

    async def remember(
        self,
        user_id: str,
        content: str,
        *,
        kind: str = "note",
        importance: int = 3,
        source_session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> LongTermMemoryEntry:
        normalized_content = _validate_content(content)
        normalized_kind = _validate_kind(kind)
        normalized_importance = _validate_importance(importance)
        if source_session_id is not None:
            source_session_id = source_session_id.strip()
            if not source_session_id or len(source_session_id) > 128:
                raise ValueError("invalid source session id")
        digest = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
        statement = text(
            """
            INSERT INTO memory.memories (
                user_id,
                source_session_id,
                kind,
                content,
                content_hash,
                importance,
                metadata,
                expires_at
            )
            VALUES (
                CAST(:user_id AS uuid),
                :source_session_id,
                :kind,
                :content,
                :content_hash,
                :importance,
                CAST(:metadata AS jsonb),
                :expires_at
            )
            ON CONFLICT (user_id, content_hash)
            DO UPDATE SET
                source_session_id = COALESCE(
                    EXCLUDED.source_session_id,
                    memory.memories.source_session_id
                ),
                kind = EXCLUDED.kind,
                content = EXCLUDED.content,
                importance = GREATEST(
                    memory.memories.importance,
                    EXCLUDED.importance
                ),
                metadata = memory.memories.metadata || EXCLUDED.metadata,
                expires_at = EXCLUDED.expires_at,
                updated_at = now()
            RETURNING
                id,
                user_id,
                source_session_id,
                kind,
                content,
                importance,
                metadata,
                created_at,
                updated_at,
                last_accessed_at,
                expires_at
            """
        )
        try:
            factory = self._session_factory()
            async with factory() as session:
                result = await session.execute(
                    statement,
                    {
                        "user_id": user_id,
                        "source_session_id": source_session_id,
                        "kind": normalized_kind,
                        "content": normalized_content,
                        "content_hash": digest,
                        "importance": normalized_importance,
                        "metadata": _metadata_json(metadata),
                        "expires_at": expires_at,
                    },
                )
                row = result.mappings().one()
                await session.commit()
                return _entry_from_mapping(row)
        except ValueError:
            raise
        except Exception as exc:
            raise LongTermMemoryPersistenceError("long-term memory storage unavailable") from exc

    async def recall(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 5,
    ) -> list[LongTermMemoryEntry]:
        if not 1 <= limit <= 20:
            raise ValueError("memory recall limit must be between 1 and 20")
        normalized_query = query.strip()[:1000]
        if normalized_query:
            statement = text(
                """
                SELECT
                    id,
                    user_id,
                    source_session_id,
                    kind,
                    content,
                    importance,
                    metadata,
                    created_at,
                    updated_at,
                    last_accessed_at,
                    expires_at,
                    GREATEST(
                        similarity(content, :query),
                        CASE
                            WHEN search_vector @@ plainto_tsquery('simple', :query)
                            THEN 0.8
                            ELSE 0.0
                        END
                    ) AS score
                FROM memory.memories
                WHERE user_id = CAST(:user_id AS uuid)
                  AND (expires_at IS NULL OR expires_at > now())
                ORDER BY score DESC, importance DESC, updated_at DESC
                LIMIT :limit
                """
            )
            params: dict[str, Any] = {
                "user_id": user_id,
                "query": normalized_query,
                "limit": limit,
            }
        else:
            statement = text(
                """
                SELECT
                    id,
                    user_id,
                    source_session_id,
                    kind,
                    content,
                    importance,
                    metadata,
                    created_at,
                    updated_at,
                    last_accessed_at,
                    expires_at,
                    NULL::real AS score
                FROM memory.memories
                WHERE user_id = CAST(:user_id AS uuid)
                  AND (expires_at IS NULL OR expires_at > now())
                ORDER BY importance DESC, updated_at DESC
                LIMIT :limit
                """
            )
            params = {"user_id": user_id, "limit": limit}

        try:
            factory = self._session_factory()
            async with factory() as session:
                result = await session.execute(statement, params)
                rows = result.mappings().all()
                entries = [
                    _entry_from_mapping(
                        row,
                        score=(float(row["score"]) if row["score"] is not None else None),
                    )
                    for row in rows
                ]
                for entry in entries:
                    await session.execute(
                        text(
                            """
                            UPDATE memory.memories
                            SET last_accessed_at = now()
                            WHERE id = CAST(:memory_id AS uuid)
                              AND user_id = CAST(:user_id AS uuid)
                            """
                        ),
                        {"memory_id": entry.id, "user_id": user_id},
                    )
                await session.commit()
                return entries
        except ValueError:
            raise
        except Exception as exc:
            raise LongTermMemoryPersistenceError("long-term memory storage unavailable") from exc

    async def list_items(
        self,
        user_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LongTermMemoryEntry]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("invalid memory pagination")
        statement = text(
            """
            SELECT
                id,
                user_id,
                source_session_id,
                kind,
                content,
                importance,
                metadata,
                created_at,
                updated_at,
                last_accessed_at,
                expires_at
            FROM memory.memories
            WHERE user_id = CAST(:user_id AS uuid)
              AND (expires_at IS NULL OR expires_at > now())
            ORDER BY importance DESC, updated_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        try:
            factory = self._session_factory()
            async with factory() as session:
                result = await session.execute(
                    statement,
                    {"user_id": user_id, "limit": limit, "offset": offset},
                )
                return [_entry_from_mapping(row) for row in result.mappings().all()]
        except ValueError:
            raise
        except Exception as exc:
            raise LongTermMemoryPersistenceError("long-term memory storage unavailable") from exc

    async def delete(self, user_id: str, memory_id: str) -> bool:
        statement = text(
            """
            DELETE FROM memory.memories
            WHERE id = CAST(:memory_id AS uuid)
              AND user_id = CAST(:user_id AS uuid)
            """
        )
        try:
            factory = self._session_factory()
            async with factory() as session:
                result = await session.execute(
                    statement,
                    {"memory_id": memory_id, "user_id": user_id},
                )
                await session.commit()
                return bool(result.rowcount)
        except Exception as exc:
            raise LongTermMemoryPersistenceError("long-term memory storage unavailable") from exc
