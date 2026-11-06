"""User-scoped persistence for explicit learning feedback."""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.embeddings import embed_text
from app.infrastructure.db import create_engine, create_session_factory
from app.modules.configuration.settings import get_settings
from app.modules.database.infrastructure import LearningExperienceORM


def _user_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except ValueError as exc:
        raise ValueError("invalid user id") from exc


class PostgresLearningStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self._factory = session_factory or create_session_factory(
            create_engine(get_settings().database_url)
        )

    @staticmethod
    async def _set_user_scope(session: AsyncSession, user_id: uuid.UUID) -> None:
        await session.execute(select(func.set_config("app.user_id", str(user_id), True)))

    async def record(
        self,
        user_id: str,
        *,
        session_id: str,
        message_ref: str,
        rating: int,
        lesson: str | None,
    ) -> dict[str, Any]:
        parsed_user = _user_uuid(user_id)
        embedding = embed_text(lesson) if lesson else None
        statement = insert(LearningExperienceORM).values(
            user_id=parsed_user,
            session_id=session_id,
            message_ref=message_ref,
            rating=rating,
            lesson=lesson,
            embedding=embedding,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_learning_experience_message",
            set_={
                "rating": statement.excluded.rating,
                "lesson": statement.excluded.lesson,
                "embedding": statement.excluded.embedding,
            },
        ).returning(LearningExperienceORM)
        async with self._factory() as session:
            async with session.begin():
                await self._set_user_scope(session, parsed_user)
                row = (await session.execute(statement)).scalar_one()
                return self._serialize(row)

    async def search(
        self, user_id: str, query: str, *, limit: int = 4
    ) -> list[dict[str, Any]]:
        parsed_user = _user_uuid(user_id)
        query_embedding = embed_text(query)
        distance = cast(Any, LearningExperienceORM.embedding).cosine_distance(query_embedding)
        async with self._factory() as session:
            async with session.begin():
                await self._set_user_scope(session, parsed_user)
                rows = await session.execute(
                    select(LearningExperienceORM, distance.label("distance"))
                    .where(
                        LearningExperienceORM.user_id == parsed_user,
                        LearningExperienceORM.lesson.is_not(None),
                    )
                    .order_by(distance.asc())
                    .limit(max(1, min(limit, 10)))
                )
                return [
                    {
                        **self._serialize(row),
                        "score": max(0.0, min(1.0, 1.0 - float(raw_distance or 0))),
                    }
                    for row, raw_distance in rows.all()
                ]

    async def list_recent(self, user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        parsed_user = _user_uuid(user_id)
        async with self._factory() as session:
            async with session.begin():
                await self._set_user_scope(session, parsed_user)
                rows = await session.execute(
                    select(LearningExperienceORM)
                    .where(LearningExperienceORM.user_id == parsed_user)
                    .order_by(LearningExperienceORM.created_at.desc())
                    .limit(max(1, min(limit, 100)))
                )
                return [self._serialize(row) for row in rows.scalars().all()]

    async def delete(self, user_id: str, experience_id: str) -> bool:
        parsed_user = _user_uuid(user_id)
        try:
            parsed_id = uuid.UUID(experience_id)
        except ValueError:
            return False
        async with self._factory() as session:
            async with session.begin():
                await self._set_user_scope(session, parsed_user)
                row = await session.scalar(
                    select(LearningExperienceORM).where(
                        LearningExperienceORM.id == parsed_id,
                        LearningExperienceORM.user_id == parsed_user,
                    )
                )
                if row is None:
                    return False
                await session.delete(row)
                return True

    @staticmethod
    def _serialize(row: LearningExperienceORM) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "session_id": row.session_id,
            "message_ref": row.message_ref,
            "rating": row.rating,
            "lesson": row.lesson,
            "created_at": row.created_at,
        }


__all__ = ["PostgresLearningStore"]
