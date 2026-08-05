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
from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app import __version__
from app.core.context import request_context_middleware
from app.core.di import build_services
from app.modules.api.rate_limit import RateLimiter
from app.modules.api.router import router as api_router
from app.modules.api.websocket import connection_manager
from app.modules.api.websocket import router as websocket_router
from app.modules.configuration.settings import Settings, get_settings
from app.modules.database.router import router as database_router
from app.modules.events.router import router as events_router
from app.modules.memory.router import router as memory_router
from app.modules.monitoring.router import router as monitoring_router
from app.modules.security.router import router as security_router

logger = structlog.get_logger("negao.main")


def _setup_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]
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


def _setup_telemetry(settings: Settings) -> None:
    if not settings.otel_exporter_otlp_endpoint:
        return
    try:
        monitoring_module = importlib.import_module("app.modules.monitoring")
        setup = getattr(monitoring_module, "setup_telemetry", None)
        if callable(setup):
            setup(settings=settings)
    except Exception:
        structlog.get_logger("negao.telemetry").warning(
            "opentelemetry setup skipped", exc_info=True
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _setup_logging(settings)
    _setup_telemetry(settings)
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


async def access_log_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    structlog.get_logger("negao.access").info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(elapsed_ms, 2),
    )
    return response


_rate_limiter: RateLimiter | None = None
_RATE_LIMIT_WHITELIST = frozenset({"/healthz", "/metrics"})


async def rate_limit_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    global _rate_limiter
    if request.url.path not in _RATE_LIMIT_WHITELIST:
        if _rate_limiter is None:
            _rate_limiter = RateLimiter(limit=get_settings().rate_limit_per_minute)
        client_ip = request.client.host if request.client else "unknown"
        allowed, limit, remaining, retry_after = await _rate_limiter.allow(client_ip)
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

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        error_logger.warning(
            "http_error",
            path=request.url.path,
            method=request.method,
            status_code=exc.status_code,
            detail=str(exc.detail),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "http_error", "detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        error_logger.warning(
            "validation_error",
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "details": jsonable_encoder(exc.errors()),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        error_logger.exception(
            "unhandled_error",
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error"},
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
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )
    _add_middlewares(application, settings)
    _register_exception_handlers(application)
    application.include_router(api_router)
    application.include_router(websocket_router)
    application.include_router(security_router)
    application.include_router(database_router)
    application.include_router(events_router)
    application.include_router(monitoring_router)
    application.include_router(memory_router)
    _add_root_healthcheck(application, settings)
    return application


app = create_app()
