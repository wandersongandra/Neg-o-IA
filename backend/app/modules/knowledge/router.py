"""Rotas do Knowledge Vault, sempre isoladas pelo usuário autenticado."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.knowledge.application import get_knowledge_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeIngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=200_000)
    source_type: Literal["manual", "markdown", "note"] = "manual"
    source_uri: str | None = Field(default=None, max_length=2048)


def _user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


@router.post("/documents")
async def ingest_document(
    body: KnowledgeIngestRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    try:
        doc = await get_knowledge_service().ingest(
            _user_id(auth),
            title=body.title,
            content=body.content,
            source_type=body.source_type,
            source_uri=body.source_uri,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "id": doc.id,
        "title": doc.title,
        "source_type": doc.source_type,
        "source_uri": doc.source_uri,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at.isoformat(),
    }


@router.get("/documents")
async def list_documents(auth: CurrentAuth) -> dict[str, Any]:
    docs = await get_knowledge_service().list_documents(_user_id(auth))
    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "source_type": doc.source_type,
                "source_uri": doc.source_uri,
                "chunk_count": doc.chunk_count,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
            }
            for doc in docs
        ]
    }


@router.get("/search")
async def search_knowledge(
    auth: CurrentAuth,
    q: str = Query(min_length=1, max_length=1000),
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    hits = await get_knowledge_service().search(_user_id(auth), q, limit=limit)
    return {
        "hits": [
            {
                "document_id": hit.document_id,
                "chunk_id": hit.chunk_id,
                "title": hit.title,
                "source_type": hit.source_type,
                "source_uri": hit.source_uri,
                "chunk_index": hit.chunk_index,
                "content": hit.content,
                "score": hit.score,
            }
            for hit in hits
        ]
    }


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, auth: CurrentAuth) -> dict[str, bool]:
    removed = await get_knowledge_service().delete_document(_user_id(auth), document_id)
    if not removed:
        raise HTTPException(status_code=404, detail="document not found")
    return {"deleted": True}
