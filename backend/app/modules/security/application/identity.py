"""Casos de uso mínimos de identidade e sessões server-side.

Tokens de sessão são opacos para o cliente e somente o hash é persistido. A
identidade efetiva vem do banco; nenhum `user_id` do payload participa da
decisão de ownership.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.settings import Settings
from app.modules.database.infrastructure import AuthSessionORM, DeviceORM, UserORM

_SCRYPT_N = 16_384
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_SESSION_TOKEN_BYTES = 48


@dataclass(frozen=True, slots=True)
class IdentityRecord:
    user_id: str
    username: str
    display_name: str | None
    device_id: str | None = None


def hash_password(password: str) -> str:
    """Deriva senha com scrypt e salt aleatório; nunca retorna a senha."""
    if len(password) < 12:
        raise ValueError("password must contain at least 12 characters")
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    )

    def encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii")

    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${encode(salt)}${encode(derived)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
        )
    except (ValueError, TypeError, UnicodeError):
        return False
    return hmac.compare_digest(actual, expected)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session_token() -> str:
    return secrets.token_urlsafe(_SESSION_TOKEN_BYTES)


async def create_user(
    session: AsyncSession,
    username: str,
    password: str,
    display_name: str | None = None,
) -> IdentityRecord:
    normalized = username.strip().lower()
    if not normalized:
        raise ValueError("username is required")
    user = UserORM(
        username=normalized,
        display_name=display_name.strip() if display_name else None,
        password_hash=hash_password(password),
    )
    session.add(user)
    await session.flush()
    if user.id is None:
        raise RuntimeError("database did not assign user id")
    return IdentityRecord(str(user.id), user.username, user.display_name)


async def authenticate_password(
    session: AsyncSession, username: str, password: str
) -> IdentityRecord | None:
    normalized = username.strip().lower()
    result = await session.execute(select(UserORM).where(UserORM.username == normalized))
    user = result.scalar_one_or_none()
    if (
        user is None
        or user.status != "active"
        or user.password_hash is None
        or not verify_password(password, user.password_hash)
    ):
        return None
    return IdentityRecord(str(user.id), user.username, user.display_name)


async def get_or_create_device(
    session: AsyncSession,
    user_id: str,
    device_name: str,
    device_type: str,
) -> str:
    """Registra o dispositivo lógico sem confiar em um ID enviado pelo cliente."""
    normalized_name = device_name.strip()[:128] or "Web Browser"
    normalized_type = device_type.strip()[:32] or "web"
    result = await session.execute(
        select(DeviceORM).where(
            DeviceORM.user_id == user_id,
            DeviceORM.device_name == normalized_name,
            DeviceORM.device_type == normalized_type,
            DeviceORM.revoked_at.is_(None),
        )
    )
    device = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if device is None:
        device = DeviceORM(
            user_id=user_id,
            device_name=normalized_name,
            device_type=normalized_type,
            created_at=now,
            last_seen_at=now,
        )
        session.add(device)
        await session.flush()
    else:
        device.last_seen_at = now
        await session.flush()
    if device.id is None:
        raise RuntimeError("database did not assign device id")
    return str(device.id)


async def persist_session(
    session: AsyncSession,
    identity: IdentityRecord,
    token: str,
    settings: Settings,
    device_id: str | None = None,
) -> datetime:
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.auth_session_ttl_seconds)
    auth_session = AuthSessionORM(
        user_id=identity.user_id,
        device_id=device_id,
        token_hash=hash_session_token(token),
        created_at=now,
        last_seen_at=now,
        expires_at=expires_at,
    )
    session.add(auth_session)
    await session.flush()
    return expires_at


async def authenticate_session(
    session: AsyncSession, token: str
) -> tuple[IdentityRecord, AuthSessionORM] | None:
    now = datetime.now(UTC)
    result = await session.execute(
        select(AuthSessionORM, UserORM)
        .join(UserORM, UserORM.id == AuthSessionORM.user_id)
        .where(
            AuthSessionORM.token_hash == hash_session_token(token),
            AuthSessionORM.revoked_at.is_(None),
            AuthSessionORM.expires_at > now,
            UserORM.status == "active",
        )
    )
    row = result.first()
    if row is None:
        return None
    auth_session, user = row
    auth_session.last_seen_at = now
    return (
        IdentityRecord(
            str(user.id),
            user.username,
            user.display_name,
            str(auth_session.device_id) if auth_session.device_id else None,
        ),
        auth_session,
    )


async def revoke_session(session: AsyncSession, session_id: str, user_id: str) -> bool:
    result = await session.execute(
        select(AuthSessionORM).where(
            AuthSessionORM.id == session_id,
            AuthSessionORM.user_id == user_id,
            AuthSessionORM.revoked_at.is_(None),
        )
    )
    auth_session = result.scalar_one_or_none()
    if auth_session is None:
        return False
    auth_session.revoked_at = datetime.now(UTC)
    await session.flush()
    return True
