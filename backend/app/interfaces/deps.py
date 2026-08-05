from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.context import get_request_context
from app.modules.security.domain import AuthResult


def get_current_auth(request: Request) -> AuthResult:
    auth = getattr(request.state, "auth_result", None)
    if not isinstance(auth, AuthResult):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )
    return auth


def get_request_id(request: Request) -> str:
    context = get_request_context()
    if context is not None:
        return context.request_id
    return request.headers.get("x-request-id") or str(uuid.uuid4())


CurrentAuth = Annotated[AuthResult, Depends(get_current_auth)]
RequestId = Annotated[str, Depends(get_request_id)]

__all__ = [
    "get_current_auth",
    "get_request_id",
    "CurrentAuth",
    "RequestId",
]
