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
    authorization_level: AuthorizationLevel = AuthorizationLevel.READ_ONLY
    reason: str | None = None
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def effective_level(self) -> AuthorizationLevel:
        if not self.authenticated:
            return AuthorizationLevel.READ_ONLY
        return self.authorization_level
