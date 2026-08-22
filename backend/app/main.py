from __future__ import annotations

import importlib
import logging
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import orjson
import structlog
from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app import __version__
from app.core.context import get_request_context, request_context_middleware
from app.core.di import build_services
from app.modules.api.rate_limit import RateLimiter
from app.modules.api.router import router as api_router
from app.modules.api.websocket import connection_manager
from app.modules.api.websocket import router as websocket_router
from app.modules.brain.router import router as brain_router
from app.modules.configuration.settings import Settings, get_settings
from app.modules.conversation.router import (
    router as conversation_router,
)
from app.modules.conversation.router import (
    ws_router as conversation_ws_router,
)
from app.modules.database.router import router as database_router
from app.modules.events.router import router as events_router
from app.modules.memory.router import router as memory_router
from app.modules.monitoring.router import router as monitoring_router
from app.modules.security.router import require_authenticated_user, require_service_auth
from app.modules.security.router import router as security_router
from app.modules.voice.router import (
    router as voice_router,
)
from app.modules.voice.router import (
    voice_ws_router,
)

logger = structlog.get_logger("negao.main")


def _setup_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]
    from app.modules.monitoring.infrastructure import redact_sensitive_fields

    shared_processors.insert(3, redact_sensitive_fields)
    if settings.env == "development":
        processors = [
            *shared_processors,
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(serializer=orjson.dumps),
        ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=level)


def _setup_telemetry(settings: Settings, application: FastAPI) -> None:
    if not settings.otel_exporter_otlp_endpoint:
        return
    try:
        monitoring_module = importlib.import_module("app.modules.monitoring")
        setup = getattr(monitoring_module, "setup_telemetry", None)
        if callable(setup):
            setup(settings=settings, fastapi_app=application)
    except Exception:
        structlog.get_logger("negao.telemetry").warning(
            "opentelemetry setup skipped", exc_info=True
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _setup_logging(settings)
    _setup_telemetry(settings, app)
    services = build_services()
    app.state.services = services
    logger.info(
        "application_started",
        name=settings.app_name,
        version=__version__,
        environment=settings.env,
    )
    yield
    try:
        await connection_manager.disconnect_all()
    except Exception:
        logger.warning("websocket_disconnect_all_failed", exc_info=True)
    logger.info("application_stopped")


async def access_log_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    try:
        from app.modules.monitoring.infrastructure import http_request_observed

        http_request_observed(
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms / 1000,
        )
    except Exception:
        logger.warning("request_metric_failed", exc_info=True)
    structlog.get_logger("sophie.access").info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(elapsed_ms, 2),
    )
    return response


_rate_limiter: RateLimiter | None = None
_RATE_LIMIT_WHITELIST = frozenset(
    {"/healthz", "/health/live", "/readyz", "/health/ready", "/metrics"}
)


def _rate_limit_key(request: Request) -> str:
    """Usa identidade autenticada ou hash de token; nunca grava credenciais."""
    auth = getattr(request.state, "auth_result", None)
    principal = getattr(auth, "effective_user_id", None)
    if isinstance(principal, str) and principal:
        return f"principal:{principal}"
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        import hashlib

        return f"token:{hashlib.sha256(authorization[7:].encode()).hexdigest()[:16]}"
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    global _rate_limiter
    if request.url.path not in _RATE_LIMIT_WHITELIST:
        if _rate_limiter is None:
            _rate_limiter = RateLimiter(limit=get_settings().rate_limit_per_minute)
        key = _rate_limit_key(request)
        allowed, limit, remaining, retry_after = await _rate_limiter.allow(key)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limited"},
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                    "Retry-After": str(retry_after),
                },
            )
    return await call_next(request)


def _add_middlewares(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BaseHTTPMiddleware, dispatch=request_context_middleware)
    app.add_middleware(BaseHTTPMiddleware, dispatch=access_log_middleware)


def _register_exception_handlers(app: FastAPI) -> None:
    error_logger = structlog.get_logger("negao.errors")

    def error_code(status_code: int) -> str:
        return {
            400: "VALIDATION_ERROR",
            401: "AUTHENTICATION_ERROR",
            403: "AUTHORIZATION_ERROR",
            404: "NOT_FOUND",
            409: "CONFLICT",
            429: "RATE_LIMITED",
            503: "DEPENDENCY_UNAVAILABLE",
        }.get(status_code, "HTTP_ERROR")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_context = get_request_context()
        request_id = request_context.request_id if request_context else None
        code = error_code(exc.status_code)
        error_logger.warning(
            "http_error",
            path=request.url.path,
            method=request.method,
            status_code=exc.status_code,
            error_code=code,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "detail": exc.detail,
                    "request_id": request_id,
                }
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_context = get_request_context()
        request_id = request_context.request_id if request_context else None
        error_logger.warning(
            "validation_error",
            path=request.url.path,
            method=request.method,
            error_code="VALIDATION_ERROR",
            request_id=request_id,
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "details": [
                        {
                            "loc": error.get("loc"),
                            "msg": error.get("msg"),
                            "type": error.get("type"),
                        }
                        for error in exc.errors()
                    ],
                    "request_id": request_id,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_context = get_request_context()
        request_id = request_context.request_id if request_context else None
        error_logger.exception(
            "unhandled_error",
            path=request.url.path,
            method=request.method,
            error_code="INTERNAL_ERROR",
            request_id=request_id,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "detail": "internal server error",
                    "request_id": request_id,
                }
            },
        )


def _add_root_healthcheck(app: FastAPI, settings: Settings) -> None:
    @app.get("/", tags=["meta"], response_model=dict[str, str])
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": __version__,
            "status": "running",
            "environment": settings.env,
        }


def create_app() -> FastAPI:
    settings = get_settings()
    docs_enabled = settings.env != "production"
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs" if docs_enabled else None,
        redoc_url=f"{settings.api_prefix}/redoc" if docs_enabled else None,
        openapi_url=f"{settings.api_prefix}/openapi.json" if docs_enabled else None,
    )
    _add_middlewares(application, settings)
    _register_exception_handlers(application)
    auth_required = [Depends(require_authenticated_user)]
    service_required = [Depends(require_service_auth)]
    # Público: meta, liveness/readiness e scrapes. Rotas de produto exigem
    # sessão de usuário; banco administrativo exige credencial de serviço.
    application.include_router(api_router)
    application.include_router(websocket_router)
    application.include_router(security_router)
    application.include_router(database_router, dependencies=service_required)
    application.include_router(events_router, dependencies=auth_required)
    application.include_router(monitoring_router)
    application.include_router(memory_router, dependencies=auth_required)
    application.include_router(brain_router, dependencies=auth_required)
    application.include_router(voice_router, dependencies=auth_required)
    application.include_router(voice_ws_router)
    application.include_router(conversation_router, dependencies=auth_required)
    application.include_router(conversation_ws_router)
    _add_root_healthcheck(application, settings)
    return application


app = create_app()
