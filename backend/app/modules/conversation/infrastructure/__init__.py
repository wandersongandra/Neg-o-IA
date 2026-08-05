"""Persistência do módulo conversation — histórico em Redis com TTL.

Estrutura:
- `conv:{session_id}:messages` — lista JSON de mensagens (TTL 24h)
- `conv:{session_id}:meta` — metadados da sessão (TTL 24h)
- `conversation:sessions` — set com todos os session_ids ativos
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.modules.conversation.domain import (
    ConversationMessage,
    ConversationSession,
)

_LOGGER = logging.getLogger("app.modules.conversation.infrastructure")

MESSAGES_TTL_SECONDS = 86400
INDEX_KEY = "conversation:sessions"
MAX_MESSAGES = 200


def _messages_key(session_id: str) -> str:
    return f"conv:{session_id}:messages"


def _meta_key(session_id: str) -> str:
    return f"conv:{session_id}:meta"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ConversationStore:
    """Store do histórico sobre Redis (fallback gracioso: redis fora = vazio)."""

    def __init__(self, redis_client: Any | None = None) -> None:
        if redis_client is None:
            from app.infrastructure.redis import get_redis

            redis_client = get_redis()
        self._redis = redis_client

    async def start_session(self, user_id: str | None) -> ConversationSession:
        session_id = uuid.uuid4().hex[:16]
        now = _now()
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            message_count=0,
        )
        try:
            await self._redis.sadd(INDEX_KEY, session_id)
            await self._redis.set(
                _meta_key(session_id),
                json.dumps(
                    {
                        "session_id": session_id,
                        "user_id": user_id,
                        "created_at": now,
                        "updated_at": now,
                        "message_count": 0,
                    }
                ),
                ex=MESSAGES_TTL_SECONDS,
            )
        except Exception:
            _LOGGER.debug("conversation_store_write_failed", exc_info=True)
        return session

    async def append_message(
        self, session_id: str, role: str, content: str
    ) -> ConversationMessage:
        message = ConversationMessage(role=role, content=content, created_at=_now())
        messages = await self.get_messages(session_id)
        messages.append(message)
        if len(messages) > MAX_MESSAGES:
            messages = messages[-MAX_MESSAGES:]
        try:
            await self._redis.set(
                _messages_key(session_id),
                json.dumps(
                    [
                        {
                            "role": m.role,
                            "content": m.content,
                            "created_at": m.created_at,
                        }
                        for m in messages
                    ]
                ),
                ex=MESSAGES_TTL_SECONDS,
            )
            await self._redis.sadd(INDEX_KEY, session_id)
            await self._touch_meta(session_id, len(messages))
        except Exception:
            _LOGGER.debug("conversation_store_append_failed", exc_info=True)
        return message

    async def _touch_meta(self, session_id: str, message_count: int) -> None:
        try:
            raw = await self._redis.get(_meta_key(session_id))
            meta: dict[str, Any] = json.loads(raw) if raw else {"session_id": session_id}
            meta["updated_at"] = _now()
            meta["message_count"] = message_count
            await self._redis.set(
                _meta_key(session_id), json.dumps(meta), ex=MESSAGES_TTL_SECONDS
            )
        except Exception:
            _LOGGER.debug("conversation_store_meta_failed", exc_info=True)

    async def get_messages(self, session_id: str) -> list[ConversationMessage]:
        try:
            raw = await self._redis.get(_messages_key(session_id))
            if not raw:
                return []
            data = json.loads(raw)
            return [
                ConversationMessage(
                    role=item["role"],
                    content=item["content"],
                    created_at=item.get("created_at", ""),
                )
                for item in data
            ]
        except Exception:
            _LOGGER.debug("conversation_store_read_failed", exc_info=True)
            return []

    async def rename_session(self, session_id: str, name: str | None) -> bool:
        """Renomeia a sessão (name opcional). Retorna False se não existir."""
        try:
            raw = await self._redis.get(_meta_key(session_id))
            if not raw:
                return False
            meta: dict[str, Any] = json.loads(raw)
            meta["name"] = name
            meta["updated_at"] = _now()
            await self._redis.set(
                _meta_key(session_id), json.dumps(meta), ex=MESSAGES_TTL_SECONDS
            )
            return True
        except Exception:
            _LOGGER.debug("conversation_store_rename_failed", exc_info=True)
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Apaga sessão (mensagens, meta e índice). Retorna False se não existir."""
        try:
            removed = await self._redis.srem(INDEX_KEY, session_id)
            if not removed:
                return False
            await self._redis.delete(_messages_key(session_id), _meta_key(session_id))
            return True
        except Exception:
            _LOGGER.debug("conversation_store_delete_failed", exc_info=True)
            return False

    async def list_sessions(self) -> list[ConversationSession]:
        try:
            ids = await self._redis.smembers(INDEX_KEY)
        except Exception:
            _LOGGER.debug("conversation_store_index_failed", exc_info=True)
            return []
        sessions: list[ConversationSession] = []
        for raw_id in sorted(ids):
            session_id = (
                raw_id.decode("utf-8") if isinstance(raw_id, bytes) else raw_id
            )
            try:
                raw = await self._redis.get(_meta_key(session_id))
                meta: dict[str, Any] = json.loads(raw) if raw else {}
                sessions.append(
                    ConversationSession(
                        session_id=session_id,
                        user_id=meta.get("user_id"),
                        created_at=meta.get("created_at", ""),
                        updated_at=meta.get("updated_at", ""),
                        message_count=int(meta.get("message_count", 0)),
                        name=meta.get("name"),
                    )
                )
            except Exception:
                _LOGGER.debug("conversation_store_meta_read_failed", exc_info=True)
        return sessions


_store: ConversationStore | None = None


def get_conversation_store() -> ConversationStore:
    """Singleton do store (redis via app.infrastructure.redis)."""
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
