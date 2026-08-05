from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

current_request: ContextVar[RequestContext | None] = ContextVar(
    "current_request", default=None
)


@dataclass(slots=True)
class RequestContext:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
        }


def get_request_context() -> RequestContext | None:
    return current_request.get()


async def request_context_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    context = RequestContext(correlation_id=request.headers.get("x-correlation-id"))
    token = current_request.set(context)
    structlog.contextvars.bind_contextvars(
        request_id=context.request_id,
        trace_id=context.trace_id,
        correlation_id=context.correlation_id,
    )
    try:
        response = await call_next(request)
    finally:
        current_request.reset(token)
        structlog.contextvars.clear_contextvars()
    response.headers["x-trace-id"] = context.trace_id
    response.headers["x-request-id"] = context.request_id
    return response
