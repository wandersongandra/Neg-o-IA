"""Rotas autenticadas do módulo Vision."""

from __future__ import annotations

import base64
import binascii
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.vision.application import VisionUnavailableError, get_vision_service
from app.modules.vision.infrastructure import VisionProviderError

router = APIRouter(prefix="/vision", tags=["vision"])


class VisionAnalyzeRequest(BaseModel):
    image_base64: str = Field(min_length=4, max_length=12_000_000)
    mime_type: Literal["image/png", "image/jpeg", "image/webp"] | None = None
    prompt: str | None = Field(default=None, max_length=4000)


def _user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


@router.get("/status")
async def vision_status() -> dict[str, Any]:
    return get_vision_service().status()


@router.post("/analyze")
async def analyze_image(
    body: VisionAnalyzeRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    try:
        image_bytes = base64.b64decode(body.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="invalid base64 image") from exc

    try:
        result = await get_vision_service().analyze(
            image_bytes,
            user_id=_user_id(auth),
            mime_type=body.mime_type,
            prompt=body.prompt,
        )
    except VisionUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VisionProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "text": result.text,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "mime_type": result.mime_type,
        "bytes_processed": result.bytes_processed,
    }
