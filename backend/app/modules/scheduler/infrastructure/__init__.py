"""Persistência PostgreSQL do Scheduler V1."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db import create_engine, create_session_factory
from app.modules.configuration.settings import get_settings
from app.modules.database.infrastructure import SchedulerJobORM
from app.modules.scheduler.domain import ScheduledJob


def _user_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except ValueError as exc:
        raise ValueError("invalid user id") from exc


def _domain(row: SchedulerJobORM) -> ScheduledJob:
    return ScheduledJob(
        id=str(row.id),
        user_id=str(row.user_id),
        name=row.name,
        action_tool=row.action_tool,
        action_args=dict(row.action_args),
        run_at=row.run_at,
        interval_seconds=row.interval_seconds,
        enabled=row.enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_run_at=row.last_run_at,
        next_run_at=row.next_run_at,
    )


class PostgresSchedulerStore:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._factory = session_factory or create_session_factory(
            create_engine(get_settings().database_url)
        )

    async def create(
        self,
        user_id: str,
        *,
        name: str,
        action_tool: str,
        action_args: dict[str, Any],
        run_at: datetime,
        interval_seconds: int | None,
    ) -> ScheduledJob:
        parsed_user = _user_uuid(user_id)
        async with self._factory() as session:
            async with session.begin():
                row = SchedulerJobORM(
                    user_id=parsed_user,
                    name=name,
                    action_tool=action_tool,
                    action_args=action_args,
                    run_at=run_at,
                    interval_seconds=interval_seconds,
                    next_run_at=run_at,
                )
                session.add(row)
                await session.flush()
                return _domain(row)

    async def list_for_user(self, user_id: str) -> list[ScheduledJob]:
        parsed_user = _user_uuid(user_id)
        async with self._factory() as session:
            result = await session.execute(
                select(SchedulerJobORM)
                .where(SchedulerJobORM.user_id == parsed_user)
                .order_by(SchedulerJobORM.created_at.desc())
            )
            return [_domain(row) for row in result.scalars()]

    async def claim_due(self, *, limit: int = 50) -> list[ScheduledJob]:
        """Claim jobs atomically so multiple replicas cannot execute the same due run."""
        now = datetime.now(UTC)
        claimed: list[ScheduledJob] = []
        async with self._factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(SchedulerJobORM)
                    .where(
                        SchedulerJobORM.enabled.is_(True),
                        SchedulerJobORM.next_run_at <= now,
                    )
                    .order_by(SchedulerJobORM.next_run_at.asc())
                    .with_for_update(skip_locked=True)
                    .limit(max(1, min(limit, 100)))
                )
                for row in result.scalars():
                    claimed.append(_domain(row))
                    row.last_run_at = now
                    row.updated_at = now
                    if row.interval_seconds is None:
                        row.enabled = False
                    else:
                        row.next_run_at = now + timedelta(seconds=row.interval_seconds)
                await session.flush()
        return claimed

    async def record_result(self, job_id: str) -> None:
        try:
            parsed = uuid.UUID(job_id)
        except ValueError:
            return
        async with self._factory() as session:
            async with session.begin():
                row = await session.get(SchedulerJobORM, parsed)
                if row is not None:
                    row.updated_at = datetime.now(UTC)
                    await session.flush()

    async def set_enabled(
        self,
        user_id: str,
        job_id: str,
        *,
        enabled: bool,
    ) -> ScheduledJob | None:
        parsed_user = _user_uuid(user_id)
        try:
            parsed_job = uuid.UUID(job_id)
        except ValueError:
            return None
        async with self._factory() as session:
            async with session.begin():
                row = await session.get(SchedulerJobORM, parsed_job)
                if row is None or row.user_id != parsed_user:
                    return None
                row.enabled = enabled
                row.updated_at = datetime.now(UTC)
                await session.flush()
                return _domain(row)

    async def delete(self, user_id: str, job_id: str) -> bool:
        parsed_user = _user_uuid(user_id)
        try:
            parsed_job = uuid.UUID(job_id)
        except ValueError:
            return False
        async with self._factory() as session:
            async with session.begin():
                row = await session.get(SchedulerJobORM, parsed_job)
                if row is None or row.user_id != parsed_user:
                    return False
                await session.delete(row)
                return True
