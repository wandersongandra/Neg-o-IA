from __future__ import annotations

import hmac
import json
import secrets
from functools import lru_cache
from typing import TYPE_CHECKING

from app.infrastructure.db import create_engine, create_session_factory
from app.modules.configuration.settings import Settings, get_settings
from app.modules.security.application import SecurityService
from app.modules.security.application.identity import authenticate_session, revoke_session
from app.modules.security.domain import AuthorizationLevel, AuthResult

if TYPE_CHECKING:
    from fastapi import WebSocket

_WS_TICKET_PREFIX = "ws_ticket:"
_WS_TICKET_TTL_SECONDS = 60
_WS_TICKET_PURPOSES = frozenset({"conversation", "voice"})


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
                principal="service:api-key",
                authorization_level=self._authorization_level,
                auth_method="service_api_key",
            )
        return AuthResult(authenticated=False, reason="invalid_service_api_key")


def create_security_service(settings: Settings) -> InMemorySecurityService:
    # A chave legada NEGAO_API_KEY nunca deve voltar a ser autoridade. O
    # fallback anterior permitia que uma credencial histórica continuasse
    # autenticando em desenvolvimento/teste quando a chave de serviço não
    # estava configurada.
    return InMemorySecurityService(expected_api_key=settings.service_api_key)


@lru_cache
def get_security_service() -> InMemorySecurityService:
    return create_security_service(get_settings())


async def issue_ws_ticket(
    principal: str,
    authorization_level: AuthorizationLevel,
    *,
    purpose: str = "conversation",
    session_id: str | None = None,
) -> str:
    """Emite um ticket de uso único para autenticar uma conexão WebSocket.

    Só deve ser chamado após uma autenticação por API key bem-sucedida (o
    endpoint que expõe isto exige `require_api_key`) — o ticket em si nunca
    é a credencial mestre, apenas uma delegação de curta duração para o
    navegador abrir o WebSocket sem nunca ver a API key real.
    """
    from app.infrastructure.redis import get_redis

    if purpose not in _WS_TICKET_PURPOSES:
        raise ValueError("invalid websocket ticket purpose")
    if purpose == "voice" and not session_id:
        raise ValueError("voice websocket ticket requires a session")
    token = secrets.token_urlsafe(32)
    payload = json.dumps(
        {
            "principal": principal,
            "authorization_level": authorization_level.value,
            "purpose": purpose,
            "session_id": session_id,
        }
    )
    await get_redis().set(f"{_WS_TICKET_PREFIX}{token}", payload, ex=_WS_TICKET_TTL_SECONDS)
    return token


async def authenticate_bearer_token(token: str) -> AuthResult:
    """Valida uma sessão persistida; falha de banco não vira 401 falso."""
    if not token or len(token) < 32:
        return AuthResult(authenticated=False, reason="invalid_session_token")
    factory = create_session_factory(create_engine(get_settings().database_url))
    async with factory() as session:
        identity_result = await authenticate_session(session, token)
        if identity_result is None:
            return AuthResult(authenticated=False, reason="invalid_or_expired_session")
        identity, auth_session = identity_result
        await session.commit()
        return AuthResult(
            authenticated=True,
            principal=identity.user_id,
            user_id=identity.user_id,
            session_id=str(auth_session.id),
            device_id=identity.device_id,
            authorization_level=AuthorizationLevel.READ_ONLY,
            auth_method="session",
        )


async def revoke_bearer_session(user_id: str, session_id: str) -> bool:
    factory = create_session_factory(create_engine(get_settings().database_url))
    async with factory() as session:
        revoked = await revoke_session(session, session_id, user_id)
        await session.commit()
        return revoked


async def redeem_ws_ticket(
    token: str,
    *,
    expected_purpose: str | None = None,
) -> AuthResult:
    """Troca um ticket por um AuthResult — uso único (GETDEL) e expira em 60s."""
    if not token:
        return AuthResult(authenticated=False, reason="missing_ticket")
    from app.infrastructure.redis import get_redis

    raw = await get_redis().getdel(f"{_WS_TICKET_PREFIX}{token}")
    if raw is None:
        return AuthResult(authenticated=False, reason="invalid_or_expired_ticket")
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("ticket payload is not an object")
        purpose = data.get("purpose", "conversation")
        principal = data["principal"]
        authorization_level = AuthorizationLevel(data["authorization_level"])
        session_id = data.get("session_id")
        if (
            not isinstance(principal, str)
            or not principal
            or not isinstance(purpose, str)
            or purpose not in _WS_TICKET_PURPOSES
            or (session_id is not None and not isinstance(session_id, str))
            or (purpose == "voice" and not session_id)
        ):
            raise ValueError("invalid ticket claims")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return AuthResult(authenticated=False, reason="invalid_ticket_payload")
    if expected_purpose and purpose != expected_purpose:
        return AuthResult(authenticated=False, reason="ticket_purpose_mismatch")
    return AuthResult(
        authenticated=True,
        principal=principal,
        user_id=principal if not principal.startswith("service:") else None,
        authorization_level=authorization_level,
        purpose=purpose,
        session_id=session_id,
        auth_method="ws_ticket",
    )


async def authenticate_ws(
    ws: WebSocket,
    *,
    expected_purpose: str | None = None,
    allow_api_key_fallback: bool = True,
) -> AuthResult:
    """Autentica uma conexão WebSocket: prioriza `?ticket=` (navegadores),
    com fallback para `?api_key=` (scripts/testes que já possuem a chave)."""
    settings = get_settings()
    origin = ws.headers.get("origin")
    if origin and settings.env == "production" and origin not in set(settings.cors_origins):
        return AuthResult(authenticated=False, reason="origin_not_allowed")
    ticket = ws.query_params.get("ticket", "")
    if ticket:
        try:
            return await redeem_ws_ticket(ticket, expected_purpose=expected_purpose)
        except Exception:
            return AuthResult(
                authenticated=False,
                reason="ticket_dependency_unavailable",
            )
    if not allow_api_key_fallback:
        return AuthResult(authenticated=False, reason="missing_ticket")
    if get_settings().env == "production":
        return AuthResult(authenticated=False, reason="api_key_fallback_disabled")
    api_key = ws.query_params.get("api_key", "")
    return get_security_service().authenticate_api_key(api_key)
