from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import String, select
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.infrastructure.cloudflare_db import (
    CloudflareAsyncEngine,
    CloudflareAsyncSession,
    create_session_factory,
)


class _Base(DeclarativeBase):
    pass


class _Record(_Base):
    __tablename__ = "cloudflare_adapter_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String(32))


@pytest.fixture
def worker_session_factory() -> Any:
    engine = create_sync_engine("sqlite://")
    _Base.metadata.create_all(engine)
    yield create_session_factory(CloudflareAsyncEngine(engine))
    engine.dispose()


@pytest.mark.asyncio
async def test_worker_session_supports_async_repository_contract(
    worker_session_factory: Any,
) -> None:
    async with worker_session_factory() as session:
        assert isinstance(session, CloudflareAsyncSession)
        async with session.begin():
            session.add(_Record(value="persisted"))
            await session.flush()
            result = await session.execute(select(_Record))
            record = result.scalar_one()
            assert record.value == "persisted"

    async with worker_session_factory() as session:
        result = await session.execute(select(_Record.value))
        assert result.scalar_one() == "persisted"


@pytest.mark.asyncio
async def test_worker_session_rolls_back_on_context_error(
    worker_session_factory: Any,
) -> None:
    with pytest.raises(RuntimeError, match="rollback sentinel"):
        async with worker_session_factory() as session:
            async with session.begin():
                session.add(_Record(value="rolled-back"))
                raise RuntimeError("rollback sentinel")

    async with worker_session_factory() as session:
        result = await session.execute(select(_Record))
        assert result.scalars().all() == []
