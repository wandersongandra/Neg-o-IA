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


class ConversationPersistenceError(RuntimeError):
    """Storage indisponível; a operação não pode ser confirmada como salva."""


class ConversationNotFoundError(LookupError):
    """Sessão inexistente ou pertencente a outro usuário."""


def _messages_key(session_id: str) -> str:
    return f"conv:{session_id}:messages"


def _meta_key(session_id: str) -> str:
    return f"conv:{session_id}:meta"


def _user_index_key(user_id: str) -> str:
    return f"conversation:sessions:user:{user_id}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ConversationStore:
    """Store do histórico sobre Redis; falha de storage é explícita."""

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
        if not user_id:
            raise ValueError("conversation session requires an authenticated user")
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.sadd(INDEX_KEY, session_id)
                pipe.sadd(_user_index_key(user_id), session_id)
                pipe.set(
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
                await pipe.execute()
        except Exception as exc:
            _LOGGER.exception("conversation_store_write_failed")
            raise ConversationPersistenceError("conversation storage unavailable") from exc
        return session

    async def append_message(self, session_id: str, role: str, content: str) -> ConversationMessage:
        message = ConversationMessage(role=role, content=content, created_at=_now())
        if await self.get_session(session_id) is None:
            raise ConversationNotFoundError(session_id)
        messages = await self.get_messages(session_id)
        messages.append(message)
        if len(messages) > MAX_MESSAGES:
            messages = messages[-MAX_MESSAGES:]
        try:
            raw_meta = await self._redis.get(_meta_key(session_id))
            meta: dict[str, Any] = json.loads(raw_meta) if raw_meta else {}
            meta["session_id"] = session_id
            meta["updated_at"] = _now()
            meta["message_count"] = len(messages)
            payload = json.dumps(
                [
                    {
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at,
                    }
                    for m in messages
                ]
            )
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.set(_messages_key(session_id), payload, ex=MESSAGES_TTL_SECONDS)
                pipe.sadd(INDEX_KEY, session_id)
                pipe.set(
                    _meta_key(session_id),
                    json.dumps(meta),
                    ex=MESSAGES_TTL_SECONDS,
                )
                await pipe.execute()
        except Exception as exc:
            _LOGGER.exception("conversation_store_append_failed")
            raise ConversationPersistenceError("conversation storage unavailable") from exc
        return message

    async def _touch_meta(self, session_id: str, message_count: int) -> None:
        raw = await self._redis.get(_meta_key(session_id))
        meta: dict[str, Any] = json.loads(raw) if raw else {"session_id": session_id}
        meta["updated_at"] = _now()
        meta["message_count"] = message_count
        await self._redis.set(_meta_key(session_id), json.dumps(meta), ex=MESSAGES_TTL_SECONDS)

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
        except Exception as exc:
            _LOGGER.exception("conversation_store_read_failed")
            raise ConversationPersistenceError("conversation storage unavailable") from exc

    async def get_session(self, session_id: str) -> ConversationSession | None:
        try:
            raw = await self._redis.get(_meta_key(session_id))
        except Exception as exc:
            raise ConversationPersistenceError("conversation storage unavailable") from exc
        if not raw:
            return None
        try:
            meta: dict[str, Any] = json.loads(raw)
            return ConversationSession(
                session_id=session_id,
                user_id=meta.get("user_id"),
                created_at=meta.get("created_at", ""),
                updated_at=meta.get("updated_at", ""),
                message_count=int(meta.get("message_count", 0)),
                name=meta.get("name"),
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ConversationPersistenceError("invalid conversation metadata") from exc

    async def get_owned_session(self, session_id: str, user_id: str) -> ConversationSession | None:
        session = await self.get_session(session_id)
        if session is None or session.user_id != user_id:
            return None
        return session

    async def rename_session(self, session_id: str, name: str | None) -> bool:
        """Renomeia a sessão (name opcional). Retorna False se não existir."""
        session = await self.get_session(session_id)
        if session is None:
            return False
        try:
            raw = await self._redis.get(_meta_key(session_id))
            if not raw:
                return False
            meta: dict[str, Any] = json.loads(raw)
            meta["name"] = name
            meta["updated_at"] = _now()
            await self._redis.set(_meta_key(session_id), json.dumps(meta), ex=MESSAGES_TTL_SECONDS)
            return True
        except Exception as exc:
            raise ConversationPersistenceError("conversation storage unavailable") from exc

    async def delete_session(self, session_id: str) -> bool:
        """Apaga sessão (mensagens, meta e índice). Retorna False se não existir."""
        session = await self.get_session(session_id)
        if session is None:
            return False
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.srem(INDEX_KEY, session_id)
                if session.user_id:
                    pipe.srem(_user_index_key(session.user_id), session_id)
                pipe.delete(_messages_key(session_id), _meta_key(session_id))
                result = await pipe.execute()
            if not result or not result[0]:
                return False
            return True
        except Exception as exc:
            raise ConversationPersistenceError("conversation storage unavailable") from exc

    async def reset_session(self, session_id: str, user_id: str) -> bool:
        session = await self.get_owned_session(session_id, user_id)
        if session is None:
            return False
        try:
            raw_meta = await self._redis.get(_meta_key(session_id))
            meta: dict[str, Any] = json.loads(raw_meta) if raw_meta else {}
            meta["session_id"] = session_id
            meta["updated_at"] = _now()
            meta["message_count"] = 0
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.delete(_messages_key(session_id))
                pipe.set(
                    _meta_key(session_id),
                    json.dumps(meta),
                    ex=MESSAGES_TTL_SECONDS,
                )
                await pipe.execute()
            return True
        except Exception as exc:
            raise ConversationPersistenceError("conversation storage unavailable") from exc

    async def list_sessions(self) -> list[ConversationSession]:
        try:
            ids = await self._redis.smembers(INDEX_KEY)
        except Exception as exc:
            raise ConversationPersistenceError("conversation storage unavailable") from exc
        sessions: list[ConversationSession] = []
        for raw_id in sorted(ids):
            session_id = raw_id.decode("utf-8") if isinstance(raw_id, bytes) else raw_id
            session = await self.get_session(session_id)
            if session is not None:
                sessions.append(session)
        return sessions

    async def list_sessions_for_user(self, user_id: str) -> list[ConversationSession]:
        try:
            ids = await self._redis.smembers(_user_index_key(user_id))
        except Exception as exc:
            raise ConversationPersistenceError("conversation storage unavailable") from exc
        sessions: list[ConversationSession] = []
        for raw_id in sorted(ids):
            session_id = raw_id.decode("utf-8") if isinstance(raw_id, bytes) else raw_id
            session = await self.get_owned_session(session_id, user_id)
            if session is not None:
                sessions.append(session)
        return sessions


_store: ConversationStore | None = None


def get_conversation_store() -> ConversationStore:
    """Singleton do store (redis via app.infrastructure.redis)."""
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
