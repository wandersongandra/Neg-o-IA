from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum


class AuthorizationLevel(IntEnum):
    READ_ONLY = 1
    SUGGEST = 2
    CONFIRM_EXECUTION = 3
    AUTO_EXECUTE = 4


@dataclass(frozen=True, slots=True)
class APIKeyCredential:
    key: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    authorization_level: AuthorizationLevel = AuthorizationLevel.READ_ONLY


@dataclass(frozen=True, slots=True)
class AuthResult:
    authenticated: bool
    principal: str | None = None
    user_id: str | None = None
    authorization_level: AuthorizationLevel = AuthorizationLevel.READ_ONLY
    reason: str | None = None
    purpose: str | None = None
    session_id: str | None = None
    device_id: str | None = None
    auth_method: str | None = None
    scopes: frozenset[str] = frozenset()
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def effective_level(self) -> AuthorizationLevel:
        if not self.authenticated:
            return AuthorizationLevel.READ_ONLY
        return self.authorization_level

    @property
    def effective_user_id(self) -> str | None:
        """Identidade canônica para ownership, nunca um valor do payload."""
        return self.user_id or self.principal
