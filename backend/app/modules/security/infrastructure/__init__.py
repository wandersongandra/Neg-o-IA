from __future__ import annotations

import hmac
from functools import lru_cache

from app.modules.configuration.settings import Settings, get_settings
from app.modules.security.application import SecurityService
from app.modules.security.domain import AuthorizationLevel, AuthResult


class InMemorySecurityService(SecurityService):
    def __init__(
        self,
        expected_api_key: str,
        authorization_level: AuthorizationLevel = AuthorizationLevel.READ_ONLY,
    ) -> None:
        self._expected_api_key = expected_api_key
        self._authorization_level = authorization_level

    def authenticate_api_key(self, key: str) -> AuthResult:
        if not key or not self._expected_api_key:
            return AuthResult(authenticated=False, reason="missing_api_key")
        if hmac.compare_digest(key.encode("utf-8"), self._expected_api_key.encode("utf-8")):
            return AuthResult(
                authenticated=True,
                principal="api_key",
                authorization_level=self._authorization_level,
            )
        return AuthResult(authenticated=False, reason="invalid_api_key")


def create_security_service(settings: Settings) -> InMemorySecurityService:
    return InMemorySecurityService(expected_api_key=settings.api_key)


@lru_cache
def get_security_service() -> InMemorySecurityService:
    return create_security_service(get_settings())
