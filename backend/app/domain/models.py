"""Entidades de domínio do NEGÃO AI.

Atenção: este módulo é framework-free — apenas dataclasses puras.
Modelos ORM (SQLAlchemy) vivem em `app.modules.database.infrastructure`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ApiKeyRecord:
    id: str
    key_hash: str
    name: str
    scopes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass(slots=True)
class UserRecord:
    id: str
    username: str
    display_name: str | None = None
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class AuditEventRecord:
    id: str
    event_type: str
    version: int
    producer: str
    payload: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    correlation_id: str | None = None
    parent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class AppConfigRecord:
    key: str
    value: Any
    updated_at: datetime = field(default_factory=datetime.now)
