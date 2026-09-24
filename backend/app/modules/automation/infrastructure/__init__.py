"""Persistência PostgreSQL das regras de automação."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db import create_engine, create_session_factory
from app.modules.automation.domain import AutomationRule
from app.modules.configuration.settings import get_settings
from app.modules.database.infrastructure import AutomationRuleORM


def _user_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except ValueError as exc:
        raise ValueError("invalid user id") from exc


def _domain(row: AutomationRuleORM) -> AutomationRule:
    return AutomationRule(
        id=str(row.id),
        user_id=str(row.user_id),
        name=row.name,
        event_type=row.event_type,
        action_tool=row.action_tool,
        action_args=dict(row.action_args),
        enabled=row.enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_triggered_at=row.last_triggered_at,
    )


class PostgresAutomationRuleStore:
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
        event_type: str,
        action_tool: str,
        action_args: dict[str, Any],
        enabled: bool,
    ) -> AutomationRule:
        parsed_user = _user_uuid(user_id)
        async with self._factory() as session:
            async with session.begin():
                row = AutomationRuleORM(
                    user_id=parsed_user,
                    name=name,
                    event_type=event_type,
                    action_tool=action_tool,
                    action_args=action_args,
                    enabled=enabled,
                )
                session.add(row)
                await session.flush()
                return _domain(row)

    async def list_for_user(self, user_id: str) -> list[AutomationRule]:
        parsed_user = _user_uuid(user_id)
        async with self._factory() as session:
            result = await session.execute(
                select(AutomationRuleORM)
                .where(AutomationRuleORM.user_id == parsed_user)
                .order_by(AutomationRuleORM.created_at.desc())
            )
            return [_domain(row) for row in result.scalars()]

    async def list_for_event(
        self,
        user_id: str,
        event_type: str,
    ) -> list[AutomationRule]:
        parsed_user = _user_uuid(user_id)
        async with self._factory() as session:
            result = await session.execute(
                select(AutomationRuleORM)
                .where(
                    AutomationRuleORM.user_id == parsed_user,
                    AutomationRuleORM.event_type == event_type,
                    AutomationRuleORM.enabled.is_(True),
                )
                .order_by(AutomationRuleORM.created_at.asc())
            )
            return [_domain(row) for row in result.scalars()]

    async def set_enabled(
        self,
        user_id: str,
        rule_id: str,
        *,
        enabled: bool,
    ) -> AutomationRule | None:
        parsed_user = _user_uuid(user_id)
        try:
            parsed_rule = uuid.UUID(rule_id)
        except ValueError:
            return None
        async with self._factory() as session:
            async with session.begin():
                row = await session.get(AutomationRuleORM, parsed_rule)
                if row is None or row.user_id != parsed_user:
                    return None
                row.enabled = enabled
                row.updated_at = datetime.now(UTC)
                await session.flush()
                return _domain(row)

    async def mark_triggered(self, user_id: str, rule_id: str) -> None:
        parsed_user = _user_uuid(user_id)
        try:
            parsed_rule = uuid.UUID(rule_id)
        except ValueError:
            return
        async with self._factory() as session:
            async with session.begin():
                row = await session.get(AutomationRuleORM, parsed_rule)
                if row is None or row.user_id != parsed_user:
                    return
                row.last_triggered_at = datetime.now(UTC)
                row.updated_at = datetime.now(UTC)
                await session.flush()

    async def delete(self, user_id: str, rule_id: str) -> bool:
        parsed_user = _user_uuid(user_id)
        try:
            parsed_rule = uuid.UUID(rule_id)
        except ValueError:
            return False
        async with self._factory() as session:
            async with session.begin():
                row = await session.get(AutomationRuleORM, parsed_rule)
                if row is None or row.user_id != parsed_user:
                    return False
                await session.delete(row)
                return True
