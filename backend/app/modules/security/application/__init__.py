from __future__ import annotations

from typing import Protocol

from app.modules.security.domain import AuthResult


class SecurityService(Protocol):
    def authenticate_api_key(self, key: str) -> AuthResult: ...


class AuthenticateApiKeyUseCase:
    def __init__(self, service: SecurityService) -> None:
        self._service = service

    def execute(self, key: str) -> AuthResult:
        return self._service.authenticate_api_key(key)
