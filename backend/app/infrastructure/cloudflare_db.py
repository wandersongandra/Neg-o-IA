"""SQLAlchemy compatibility layer for Python Workers.

Cloudflare's Python runtime supports synchronous SQLAlchemy but does not ship
greenlet, which SQLAlchemy's async extension requires. This module keeps the
application's async repository contract while serializing each synchronous
SQLAlchemy operation for a single session. PostgreSQL connections are routed
through a Hyperdrive binding.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy import Engine
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

T = TypeVar("T")


class CloudflareAsyncConnection:
    def __init__(self, connection: Any) -> None:
        self._connection = connection
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> CloudflareAsyncConnection:
        return self

    def __await__(self) -> Any:
        async def resolved() -> CloudflareAsyncConnection:
            return self

        return resolved().__await__()

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        return await self._run(lambda: self._connection.execute(*args, **kwargs))

    async def close(self) -> None:
        await self._run(self._connection.close)

    async def _run(self, operation: Callable[[], T]) -> T:
        async with self._lock:
            return operation()


class CloudflareAsyncTransaction:
    def __init__(self, session: CloudflareAsyncSession, nested: bool = False) -> None:
        self._session = session
        self._transaction = session._session.begin_nested() if nested else session._session.begin()

    async def __aenter__(self) -> CloudflareAsyncTransaction:
        await self._session._run(self._transaction.__enter__)
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool | None:
        return await self._session._run(
            lambda: self._transaction.__exit__(exc_type, exc, traceback)
        )


class CloudflareAsyncSession:
    """Async-shaped session facade over one synchronous ORM Session."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> CloudflareAsyncSession:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self.close()

    def begin(self) -> CloudflareAsyncTransaction:
        return CloudflareAsyncTransaction(self)

    def begin_nested(self) -> CloudflareAsyncTransaction:
        return CloudflareAsyncTransaction(self, nested=True)

    def add(self, instance: Any, _warn: bool = True) -> None:
        self._session.add(instance, _warn=_warn)

    def add_all(self, instances: Any) -> None:
        self._session.add_all(instances)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        return await self._run(lambda: self._session.execute(*args, **kwargs))

    async def scalar(self, *args: Any, **kwargs: Any) -> Any:
        return await self._run(lambda: self._session.scalar(*args, **kwargs))

    async def scalars(self, *args: Any, **kwargs: Any) -> Any:
        return await self._run(lambda: self._session.scalars(*args, **kwargs))

    async def get(self, *args: Any, **kwargs: Any) -> Any:
        return await self._run(lambda: self._session.get(*args, **kwargs))

    async def delete(self, instance: Any) -> None:
        await self._run(lambda: self._session.delete(instance))

    async def flush(self, *args: Any, **kwargs: Any) -> None:
        await self._run(lambda: self._session.flush(*args, **kwargs))

    async def commit(self) -> None:
        await self._run(self._session.commit)

    async def rollback(self) -> None:
        await self._run(self._session.rollback)

    async def refresh(self, instance: Any, *args: Any, **kwargs: Any) -> None:
        await self._run(lambda: self._session.refresh(instance, *args, **kwargs))

    async def close(self) -> None:
        await self._run(self._session.close)

    async def _run(self, operation: Callable[[], T]) -> T:
        async with self._lock:
            return operation()


class CloudflareAsyncSessionFactory:
    def __init__(self, engine: CloudflareAsyncEngine) -> None:
        self._factory = sessionmaker(engine.sync_engine, expire_on_commit=False)

    def __call__(self) -> CloudflareAsyncSession:
        return CloudflareAsyncSession(self._factory())


class CloudflareAsyncEngine:
    def __init__(self, engine: Engine) -> None:
        self.sync_engine = engine

    @property
    def url(self) -> URL:
        return self.sync_engine.url

    def connect(self) -> CloudflareAsyncConnection:
        return CloudflareAsyncConnection(self.sync_engine.connect())

    async def dispose(self) -> None:
        self.sync_engine.dispose()


_hyperdrive: Any | None = None


def configure_hyperdrive(binding: Any) -> None:
    """Set the per-isolate Hyperdrive binding before handling the request."""
    global _hyperdrive
    _hyperdrive = binding


def _hyperdrive_url() -> URL:
    if _hyperdrive is None:
        raise RuntimeError("Cloudflare Hyperdrive binding is not configured")
    connection_string = getattr(_hyperdrive, "connectionString", None)
    if isinstance(connection_string, str) and connection_string:
        return make_url(connection_string).set(drivername="postgresql+pg8000")
    try:
        return URL.create(
            "postgresql+pg8000",
            username=str(_hyperdrive.user),
            password=str(_hyperdrive.password),
            host=str(_hyperdrive.host),
            port=int(_hyperdrive.port),
            database=str(_hyperdrive.database),
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError("Cloudflare Hyperdrive binding is incomplete") from exc


def create_engine(database_url: str, *, echo: bool = False) -> CloudflareAsyncEngine:
    """Create an engine that leaves connection pooling to Hyperdrive."""
    del database_url  # Credentials come only from the bound Hyperdrive object.
    engine = create_sync_engine(
        _hyperdrive_url(),
        poolclass=NullPool,
        echo=echo,
    )
    return CloudflareAsyncEngine(engine)


def create_session_factory(engine: CloudflareAsyncEngine) -> CloudflareAsyncSessionFactory:
    return CloudflareAsyncSessionFactory(engine)
