"""Rotas autenticadas do Tool Manager."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.tool_manager.application import (
    ToolCircuitOpenError,
    ToolConfirmationRequiredError,
    ToolNotFoundError,
    get_tool_manager_service,
)

router = APIRouter(prefix="/tool-manager", tags=["tool_manager"])


class ExecuteToolRequest(BaseModel):
    tool_name: str = Field(min_length=1, max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)


def _user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


@router.get("/catalog")
async def tool_catalog() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": spec.name,
                "description": spec.description,
                "input_schema": spec.input_schema,
                "risk": spec.risk,
                "requires_confirmation": spec.requires_confirmation,
                "automation_safe": spec.automation_safe,
            }
            for spec in get_tool_manager_service().catalog()
        ]
    }


@router.post("/execute")
async def execute_tool(
    body: ExecuteToolRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    try:
        result = await get_tool_manager_service().execute_tool(
            body.tool_name,
            body.arguments,
            user_id=_user_id(auth),
            confirmed=body.confirmed,
            idempotency_key=body.idempotency_key,
        )
    except ToolNotFoundError as exc:
        raise HTTPException(status_code=404, detail="tool not found") from exc
    except ToolConfirmationRequiredError as exc:
        raise HTTPException(status_code=409, detail="confirmation required") from exc
    except ToolCircuitOpenError as exc:
        raise HTTPException(status_code=503, detail="tool circuit open") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "tool_name": result.tool_name,
        "output": result.output,
        "cached": result.cached,
    }
