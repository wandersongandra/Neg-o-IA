"""Autenticação de usuários, sessões server-side e auth de serviços.

API keys permanecem somente como credencial explícita de serviço em
desenvolvimento/infraestrutura. Usuários finais usam sessão Bearer persistida;
nenhum `user_id` recebido do cliente é autoridade.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.context import get_request_context
from app.infrastructure.db import create_engine, create_session_factory
from app.modules.api.rate_limit import RateLimiter, trusted_client_ip
from app.modules.configuration.settings import get_settings
from app.modules.database.application import PERSISTED_API_KEY_PREFIX, verify_api_key
from app.modules.security.application.identity import (
    authenticate_password,
    create_user,
    get_or_create_device,
    issue_session_token,
    persist_session,
)
from app.modules.security.domain import AuthorizationLevel, AuthResult
from app.modules.security.infrastructure import (
    authenticate_bearer_token,
    get_security_service,
    issue_ws_ticket,
    list_bearer_sessions,
    revoke_bearer_session,
    revoke_other_bearer_sessions,
)

router = APIRouter(prefix="/security", tags=["security"])

_logger = structlog.get_logger("sophie.security")
_AUTH_EVENT_PUBLISH_TIMEOUT = 2.0
_login_limiter: RateLimiter | None = None
_DEV_SESSION_COOKIE = "sophie_session"
_PROD_SESSION_COOKIE = "__Host-sophie_session"


def _session_cookie_name() -> str:
    return _PROD_SESSION_COOKIE if get_settings().env == "production" else _DEV_SESSION_COOKIE


def _get_login_limiter() -> RateLimiter:
    global _login_limiter
    if _login_limiter is None:
        _login_limiter = RateLimiter(
            limit=get_settings().rate_limit_burst,
            fail_closed=get_settings().env == "production",
        )
    return _login_limiter


async def _enforce_login_rate_limit(request: Request, username: str) -> None:
    """Aplica buckets independentes por IP e por conta para reduzir brute force."""
    limiter = _get_login_limiter()
    client_ip = trusted_client_ip(request)
    normalized = username.strip().lower()
    user_bucket = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
    retry_after = 0
    allowed = True
    for bucket in (f"login:ip:{client_ip}", f"login:user:{user_bucket}"):
        bucket_allowed, _, _, bucket_retry = await limiter.allow(bucket)
        allowed = allowed and bucket_allowed
        retry_after = max(retry_after, bucket_retry)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many login attempts",
            headers={"Retry-After": str(max(1, retry_after))},
        )


class CredentialRequest(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=12, max_length=128)
    display_name: str | None = Field(default=None, max_length=256)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=1, max_length=128)
    device_name: str | None = Field(default=None, max_length=128)
    device_type: str | None = Field(default=None, max_length=32)


class WsTicketRequest(BaseModel):
    purpose: Literal["conversation", "voice"] = "conversation"
    session_id: str | None = Field(default=None, min_length=1, max_length=64)


class SessionResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int
    user_id: str
    username: str
    display_name: str | None = None


class ActiveSessionResponse(BaseModel):
    session_id: str
    current: bool
    device_id: str | None = None
    device_name: str | None = None
    device_type: str | None = None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


def _set_auth_context(request: Request, result: AuthResult) -> None:
    request.state.auth_result = result
    context = get_request_context()
    if context is not None:
        context.user_id = result.effective_user_id
        context.session_id = result.session_id
        structlog.contextvars.bind_contextvars(
            user_id=result.effective_user_id,
            auth_method=result.auth_method,
        )


async def _publish_auth_event(event_type: str, result: AuthResult) -> None:
    from app.modules.events.application import get_event_bus_service
    from app.modules.events.envelope import build_envelope

    envelope = build_envelope(
        event_type,
        producer="security",
        user_id=result.effective_user_id,
        session_id=result.session_id,
        payload={
            "authorization_level": result.authorization_level.name,
            "auth_method": result.auth_method,
            "reason": result.reason,
        },
    )
    await asyncio.wait_for(
        get_event_bus_service().publish_event(envelope),
        timeout=_AUTH_EVENT_PUBLISH_TIMEOUT,
    )


def _unauthorized(detail: str = "authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _validate_cookie_request_origin(request: Request) -> None:
    """Impede CSRF quando a sessão chega como cookie em produção."""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if get_settings().env != "production":
        return
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site and fetch_site != "same-origin":
        raise HTTPException(status_code=403, detail="cross-site request blocked")
    fetch_destination = request.headers.get("sec-fetch-dest")
    if fetch_destination and fetch_destination != "empty":
        raise HTTPException(status_code=403, detail="unexpected fetch destination")
    origin = request.headers.get("origin")
    if origin not in set(get_settings().cors_origins):
        raise HTTPException(status_code=403, detail="request origin not allowed")


async def require_authenticated_user(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session_cookie: Annotated[str | None, Cookie(alias="sophie_session")] = None,
    host_session_cookie: Annotated[
        str | None,
        Cookie(alias="__Host-sophie_session"),
    ] = None,
) -> AuthResult:
    """Resolve usuário exclusivamente por sessão server-side."""
    token = ""
    cookie_token = host_session_cookie if get_settings().env == "production" else session_cookie
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif cookie_token:
        token = cookie_token

    if token:
        if cookie_token and not authorization:
            _validate_cookie_request_origin(request)
        try:
            result = await authenticate_bearer_token(token)
        except Exception as exc:
            # O driver async pode propagar falhas de conexão como exceções
            # nativas (por exemplo, ConnectionRefusedError) antes de o
            # SQLAlchemy conseguir encapsulá-las. Nesta fronteira de
            # autenticação, qualquer falha de dependência deve ser fail-closed
            # e nunca virar 500 ou uma falsa resposta de não autenticado.
            _logger.exception("authentication_database_unavailable")
            raise HTTPException(
                status_code=503, detail="authentication dependency unavailable"
            ) from exc
        if not result.authenticated:
            raise _unauthorized("invalid or expired session")
    else:
        raise _unauthorized()

    _set_auth_context(request, result)
    try:
        await _publish_auth_event("security.auth.completed", result)
    except Exception:
        _logger.warning("auth_completed_event_publish_error", exc_info=True)
    return result


async def require_service_auth(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> AuthResult:
    """Autentica chave bootstrap ou chave rotacionável persistida no banco."""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="service authentication required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    result = get_security_service().authenticate_api_key(x_api_key)
    if not result.authenticated and x_api_key.startswith(PERSISTED_API_KEY_PREFIX):
        factory = create_session_factory(create_engine(get_settings().database_url))
        try:
            async with factory() as session:
                record = await verify_api_key(session, x_api_key)
                if record is not None:
                    await session.commit()
                    result = AuthResult(
                        authenticated=True,
                        principal=f"service:db-key:{record.id}",
                        authorization_level=AuthorizationLevel.AUTO_EXECUTE,
                        auth_method="database_api_key",
                        scopes=frozenset(record.scopes),
                    )
        except SQLAlchemyError as exc:
            _logger.exception("service_auth_database_unavailable")
            raise HTTPException(
                status_code=503, detail="service authentication dependency unavailable"
            ) from exc
    if not result.authenticated:
        raise HTTPException(
            status_code=401,
            detail="invalid service credential",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    _set_auth_context(request, result)
    return result


def require_service_scope(scope: str) -> Callable[..., Awaitable[AuthResult]]:
    async def dependency(
        auth: Annotated[AuthResult, Depends(require_service_auth)],
    ) -> AuthResult:
        if scope not in auth.scopes:
            raise HTTPException(status_code=403, detail="service scope required")
        return auth

    return dependency


async def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> AuthResult:
    """Alias legado para serviços; não deve ser usado em rotas de usuário."""
    return await require_service_auth(request, x_api_key)


@router.post("/register", response_model=dict[str, str], status_code=201)
async def register(body: CredentialRequest) -> dict[str, str]:
    if not get_settings().registration_enabled:
        raise HTTPException(status_code=404, detail="registration disabled")
    factory = create_session_factory(create_engine(get_settings().database_url))
    try:
        async with factory() as session:
            identity = await create_user(
                session,
                body.username,
                body.password,
                body.display_name,
            )
            await session.commit()
            return {"user_id": identity.user_id, "username": identity.username}
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="username already exists") from exc
    except SQLAlchemyError as exc:
        _logger.exception("registration_database_unavailable")
        raise HTTPException(status_code=503, detail="identity dependency unavailable") from exc


@router.post("/login", response_model=SessionResponse)
async def login(body: LoginRequest, response: Response, request: Request) -> SessionResponse:
    await _enforce_login_rate_limit(request, body.username)
    factory = create_session_factory(create_engine(get_settings().database_url))
    try:
        async with factory() as session:
            identity = await authenticate_password(session, body.username, body.password)
            if identity is None:
                raise _unauthorized("invalid credentials")
            token = issue_session_token()
            device_id = await get_or_create_device(
                session,
                identity.user_id,
                body.device_name or "Web Browser",
                body.device_type or "web",
            )
            expires_at = await persist_session(
                session,
                identity,
                token,
                get_settings(),
                device_id=device_id,
            )
            await session.commit()
            response.set_cookie(
                _session_cookie_name(),
                token,
                max_age=get_settings().auth_session_ttl_seconds,
                httponly=True,
                secure=get_settings().env == "production",
                samesite="strict",
                path="/",
            )
            return SessionResponse(
                access_token=token,
                expires_in=max(0, int((expires_at - datetime.now(UTC)).total_seconds())),
                user_id=identity.user_id,
                username=identity.username,
                display_name=identity.display_name,
            )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        _logger.exception("login_database_unavailable")
        raise HTTPException(status_code=503, detail="identity dependency unavailable") from exc


@router.post("/logout", status_code=204, response_model=None)
async def logout(
    response: Response,
    auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> None:
    if auth.auth_method == "session" and auth.effective_user_id and auth.session_id:
        try:
            await revoke_bearer_session(auth.effective_user_id, auth.session_id)
        except SQLAlchemyError as exc:
            _logger.exception("logout_database_unavailable")
            raise HTTPException(status_code=503, detail="identity dependency unavailable") from exc
    response.delete_cookie(_DEV_SESSION_COOKIE, path="/")
    response.delete_cookie(_PROD_SESSION_COOKIE, path="/", secure=True, samesite="strict")


@router.get("/sessions", response_model=list[ActiveSessionResponse])
async def active_sessions(
    auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> list[ActiveSessionResponse]:
    if not auth.effective_user_id or not auth.session_id:
        raise HTTPException(status_code=403, detail="user session required")
    try:
        records = await list_bearer_sessions(auth.effective_user_id)
    except SQLAlchemyError as exc:
        _logger.exception("session_inventory_database_unavailable")
        raise HTTPException(status_code=503, detail="identity dependency unavailable") from exc
    return [
        ActiveSessionResponse(
            session_id=record.session_id,
            current=record.session_id == auth.session_id,
            device_id=record.device_id,
            device_name=record.device_name,
            device_type=record.device_type,
            created_at=record.created_at,
            last_seen_at=record.last_seen_at,
            expires_at=record.expires_at,
        )
        for record in records
    ]


@router.delete("/sessions/{session_id}", status_code=204, response_model=None)
async def revoke_named_session(
    session_id: str,
    auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> None:
    if not auth.effective_user_id or not auth.session_id:
        raise HTTPException(status_code=403, detail="user session required")
    if session_id == auth.session_id:
        raise HTTPException(status_code=409, detail="use logout for the current session")
    try:
        revoked = await revoke_bearer_session(auth.effective_user_id, session_id)
    except SQLAlchemyError as exc:
        _logger.exception("session_revoke_database_unavailable")
        raise HTTPException(status_code=503, detail="identity dependency unavailable") from exc
    if not revoked:
        raise HTTPException(status_code=404, detail="session not found")


@router.post("/sessions/revoke-others")
async def revoke_other_sessions_endpoint(
    auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> dict[str, int]:
    if not auth.effective_user_id or not auth.session_id:
        raise HTTPException(status_code=403, detail="user session required")
    try:
        revoked = await revoke_other_bearer_sessions(
            auth.effective_user_id,
            auth.session_id,
        )
    except SQLAlchemyError as exc:
        _logger.exception("session_bulk_revoke_database_unavailable")
        raise HTTPException(status_code=503, detail="identity dependency unavailable") from exc
    return {"revoked": revoked}


@router.get("/status")
async def security_status(
    auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> dict[str, object]:
    return {
        "status": "ok",
        "authenticated": True,
        "authorization_level": auth.authorization_level.name,
        "authorization_level_id": auth.authorization_level.value,
        "principal": auth.effective_user_id,
        "user_id": auth.user_id,
        "session_id": auth.session_id,
        "device_id": auth.device_id,
        "auth_method": auth.auth_method,
    }


@router.post("/ws-ticket")
async def create_ws_ticket(
    auth: Annotated[AuthResult, Depends(require_authenticated_user)],
    body: WsTicketRequest | None = None,
) -> dict[str, object]:
    request = body or WsTicketRequest()
    if request.purpose == "voice" and not request.session_id:
        raise HTTPException(status_code=400, detail="voice ticket requires a session_id")
    if auth.effective_user_id is None:
        raise HTTPException(status_code=403, detail="user identity required")
    if request.purpose == "voice" and request.session_id:
        from app.modules.conversation.application import get_conversation_service
        from app.modules.conversation.infrastructure import ConversationPersistenceError

        try:
            owns_session = await get_conversation_service().owns_session(
                request.session_id, auth.effective_user_id
            )
        except ConversationPersistenceError as exc:
            raise HTTPException(status_code=503, detail="conversation storage unavailable") from exc
        if not owns_session:
            raise HTTPException(status_code=404, detail="session not found")
    try:
        ticket = await issue_ws_ticket(
            auth.effective_user_id,
            auth.authorization_level,
            purpose=request.purpose,
            session_id=request.session_id,
            auth_session_id=auth.session_id,
            device_id=auth.device_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ticket": ticket,
        "expires_in": 60,
        "purpose": request.purpose,
        "session_id": request.session_id,
    }
