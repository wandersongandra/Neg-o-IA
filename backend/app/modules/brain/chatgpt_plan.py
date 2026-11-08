"""Secure storage and OAuth-backed inference for an eligible ChatGPT plan."""

from __future__ import annotations

import base64
import binascii
import hmac
import json
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.db import (
    AsyncSession,
    async_sessionmaker,
    create_engine,
    create_session_factory,
)
from app.modules.configuration.settings import get_settings
from app.modules.database.infrastructure import OpenAIPlanCredentialORM, OpenAIPlanHostORM

_LOGGER = logging.getLogger("app.modules.brain.chatgpt_plan")
_AUTH_ORIGIN = "https://auth.openai.com"
_API_ORIGIN = "https://api.openai.com/v1"
_ISSUER = "https://auth.openai.com"
_REQUIRED_SCOPE = "chatgpt.tokens.use.direct"
_MAX_RESPONSE_BYTES = 1024 * 1024
_DISCOVERY_PATH = "/.well-known/openid-configuration"
_JWKS_CACHE: tuple[float, list[dict[str, Any]]] | None = None


class ChatGPTPlanError(RuntimeError):
    """A user-owned ChatGPT plan connection is unavailable or invalid."""


async def _read_limited(response: httpx.Response, limit: int) -> bytes:
    declared = response.headers.get("content-length")
    if declared:
        try:
            if int(declared) > limit:
                raise ChatGPTPlanError("A resposta externa excedeu o limite de tamanho.")
        except ValueError:
            pass
    parts: list[bytes] = []
    size = 0
    async for part in response.aiter_bytes():
        size += len(part)
        if size > limit:
            raise ChatGPTPlanError("A resposta externa excedeu o limite de tamanho.")
        parts.append(part)
    return b"".join(parts)


class ChatGPTPlanStore:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._factory = session_factory or create_session_factory(
            create_engine(get_settings().database_url)
        )

    @staticmethod
    def _key() -> bytes:
        encoded = get_settings().oauth_credential_encryption_key.strip()
        if not encoded:
            raise ChatGPTPlanError(
                "Configure SOPHIE_OAUTH_CREDENTIAL_ENCRYPTION_KEY antes de conectar o plano."
            )
        try:
            key = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        except (ValueError, binascii.Error) as exc:
            raise ChatGPTPlanError("A chave de cifra OAuth não é base64url válida.") from exc
        if len(key) != 32:
            raise ChatGPTPlanError("A chave de cifra OAuth precisa representar 32 bytes.")
        return key

    @classmethod
    def _encrypt(cls, user_id: uuid.UUID, field: str, value: str) -> bytes:
        nonce = secrets.token_bytes(12)
        aad = f"neg-o-ia:chatgpt-plan:{user_id}:{field}:v1".encode()
        return nonce + AESGCM(cls._key()).encrypt(nonce, value.encode(), aad)

    @classmethod
    def _decrypt(cls, user_id: uuid.UUID, field: str, ciphertext: bytes) -> str:
        if len(ciphertext) < 29:
            raise ChatGPTPlanError("Credencial OAuth cifrada inválida.")
        nonce, body = ciphertext[:12], ciphertext[12:]
        aad = f"neg-o-ia:chatgpt-plan:{user_id}:{field}:v1".encode()
        try:
            return AESGCM(cls._key()).decrypt(nonce, body, aad).decode()
        except (InvalidTag, ValueError, UnicodeError) as exc:
            raise ChatGPTPlanError(
                "Não foi possível decifrar as credenciais; verifique a chave configurada."
            ) from exc

    @staticmethod
    async def _set_user_scope(session: AsyncSession, user_id: uuid.UUID) -> None:
        await session.execute(select(func.set_config("app.user_id", str(user_id), True)))

    @staticmethod
    def _user_uuid(user_id: str) -> uuid.UUID:
        try:
            return uuid.UUID(user_id)
        except ValueError as exc:
            raise ChatGPTPlanError("Sessão do usuário inválida.") from exc

    async def get_host_id(self) -> str:
        host_id = f"urn:uuid:{uuid.uuid4()}"
        async with self._factory() as session:
            async with session.begin():
                statement = insert(OpenAIPlanHostORM).values(id=1, host_id=host_id)
                await session.execute(statement.on_conflict_do_nothing(index_elements=["id"]))
                value = await session.scalar(
                    select(OpenAIPlanHostORM.host_id).where(OpenAIPlanHostORM.id == 1)
                )
                if not value:
                    raise ChatGPTPlanError(
                        "Não foi possível registrar a identidade desta instalação."
                    )
                return str(value)

    async def status(self, user_id: str) -> dict[str, Any]:
        parsed_user = self._user_uuid(user_id)
        host_id = await self.get_host_id()
        async with self._factory() as session:
            async with session.begin():
                await self._set_user_scope(session, parsed_user)
                row = await session.get(OpenAIPlanCredentialORM, parsed_user)
                if row is None:
                    return {"connected": False, "host_id": host_id}
                return {
                    "connected": True,
                    "email": row.email,
                    # OAuth public client identifiers are not credentials; the
                    # local CLI needs this value to reauthorize the same client.
                    "client_id": row.client_id,
                    "expires_at": row.expires_at.isoformat(),
                    "connected_at": row.connected_at.isoformat(),
                    "host_id": host_id,
                    "plan_usage_enabled": _REQUIRED_SCOPE in row.scopes,
                }

    async def save_credentials(
        self,
        user_id: str,
        *,
        client_id: str,
        host_id: str,
        access_token: str,
        refresh_token: str,
        id_token: str,
        expected_nonce: str,
        scopes: list[str],
        expires_in: int,
    ) -> None:
        parsed_user = self._user_uuid(user_id)
        actual_host = await self.get_host_id()
        if host_id != actual_host:
            raise ChatGPTPlanError("A autorização foi emitida para outra instalação do agente.")
        if _REQUIRED_SCOPE not in scopes or "resource.invoke" not in scopes:
            raise ChatGPTPlanError("A autorização não incluiu permissão para uso do plano ChatGPT.")
        validated = await validate_identity_token(
            id_token,
            client_id=client_id,
            expected_nonce=expected_nonce,
        )
        if not 60 <= expires_in <= 86_400:
            raise ChatGPTPlanError(
                "A validade informada para o token está fora do limite permitido."
            )
        if not all((client_id, access_token, refresh_token, id_token)):
            raise ChatGPTPlanError("A resposta OAuth não contém todas as credenciais necessárias.")
        now = datetime.now(UTC)
        validated_email = validated.get("email")
        account_subject = validated.get("sub")
        if not isinstance(account_subject, str) or not account_subject:
            raise ChatGPTPlanError("O ID token não contém um identificador de conta válido.")
        values = {
            "user_id": parsed_user,
            "email": (
                validated_email
                if isinstance(validated_email, str) and len(validated_email) <= 320
                else None
            ),
            "client_id": client_id,
            "host_id": host_id,
            "access_token_cipher": self._encrypt(parsed_user, "access", access_token),
            "refresh_token_cipher": self._encrypt(parsed_user, "refresh", refresh_token),
            "account_subject_cipher": self._encrypt(parsed_user, "subject", account_subject),
            "scopes": sorted(set(scopes)),
            "expires_at": now + timedelta(seconds=expires_in),
            "updated_at": now,
        }
        async with self._factory() as session:
            async with session.begin():
                await self._set_user_scope(session, parsed_user)
                existing = await session.scalar(
                    select(OpenAIPlanCredentialORM)
                    .where(OpenAIPlanCredentialORM.user_id == parsed_user)
                    .with_for_update()
                )
                if existing is not None:
                    if existing.client_id != client_id:
                        raise ChatGPTPlanError(
                            "Desconecte a conta ChatGPT atual antes de conectar outra."
                        )
                    previous_subject = self._decrypt(
                        parsed_user, "subject", existing.account_subject_cipher
                    )
                    if not hmac.compare_digest(previous_subject, account_subject):
                        raise ChatGPTPlanError(
                            "A conta selecionada não corresponde à conexão ChatGPT existente."
                        )
                statement = insert(OpenAIPlanCredentialORM).values(**values)
                await session.execute(
                    statement.on_conflict_do_update(
                        index_elements=["user_id"],
                        set_={
                            **{key: value for key, value in values.items() if key != "user_id"},
                            "connected_at": now,
                        },
                    )
                )

    async def access_token(self, user_id: str) -> str:
        parsed_user = self._user_uuid(user_id)
        actual_host_id = await self.get_host_id()
        refresh_failure: str | None = None
        refreshed_access: str | None = None
        async with self._factory() as session:
            async with session.begin():
                await self._set_user_scope(session, parsed_user)
                row = await session.scalar(
                    select(OpenAIPlanCredentialORM)
                    .where(OpenAIPlanCredentialORM.user_id == parsed_user)
                    .with_for_update()
                )
                if row is None or _REQUIRED_SCOPE not in row.scopes:
                    raise ChatGPTPlanError("Conecte uma conta ChatGPT elegível em Configuração.")
                if row.host_id != actual_host_id:
                    raise ChatGPTPlanError("As credenciais pertencem a outra instalação do agente.")
                if row.expires_at > datetime.now(UTC) + timedelta(seconds=120):
                    return self._decrypt(parsed_user, "access", row.access_token_cipher)

                refresh_token = self._decrypt(parsed_user, "refresh", row.refresh_token_cipher)
                try:
                    refreshed = await _refresh_tokens(row.client_id, refresh_token)
                except ChatGPTPlanError as exc:
                    if "invalid_grant" in str(exc).lower() or "refresh token" in str(exc).lower():
                        await session.delete(row)
                        refresh_failure = (
                            "A autorização ChatGPT expirou ou foi revogada; "
                            "conecte a conta novamente."
                        )
                    else:
                        raise
                if refresh_failure is None:
                    raw_scopes = refreshed.get("scope", " ".join(row.scopes))
                    scopes = raw_scopes.split() if isinstance(raw_scopes, str) else []
                    if _REQUIRED_SCOPE not in scopes or "resource.invoke" not in scopes:
                        await session.delete(row)
                        refresh_failure = "O plano ChatGPT deixou de autorizar uso direto pela app."
                if refresh_failure is None:
                    expires_in = _valid_expires_in(refreshed.get("expires_in"))
                    refreshed_access = _required_string(refreshed, "access_token")
                    refreshed_refresh = refreshed.get("refresh_token", refresh_token)
                    if not isinstance(refreshed_refresh, str) or not refreshed_refresh:
                        raise ChatGPTPlanError("A resposta OAuth perdeu o refresh token da conta.")
                    row.access_token_cipher = self._encrypt(parsed_user, "access", refreshed_access)
                    row.refresh_token_cipher = self._encrypt(
                        parsed_user, "refresh", refreshed_refresh
                    )
                    row.scopes = sorted(set(scopes))
                    row.expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
                    row.updated_at = datetime.now(UTC)
        if refresh_failure is not None:
            raise ChatGPTPlanError(refresh_failure)
        if refreshed_access is None:
            raise ChatGPTPlanError("Não foi possível renovar a autorização ChatGPT.")
        return refreshed_access

    async def models(self, user_id: str) -> list[dict[str, str]]:
        token = await self.access_token(user_id)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            async with client.stream(
                "GET",
                f"{_API_ORIGIN}/models",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            ) as response:
                if response.status_code != 200:
                    raise ChatGPTPlanError(
                        f"Catálogo de modelos indisponível (HTTP {response.status_code})."
                    )
                raw = await _read_limited(response, _MAX_RESPONSE_BYTES)
        try:
            payload = json.loads(raw)
            raw_models = payload["models"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ChatGPTPlanError("A resposta de modelos está em formato inválido.") from exc
        if not isinstance(raw_models, list):
            raise ChatGPTPlanError("O catálogo de modelos está em formato inválido.")
        models: list[dict[str, str]] = []
        for model in raw_models:
            if not isinstance(model, dict) or model.get("visibility") != "list":
                continue
            slug, label = model.get("slug"), model.get("display_name")
            if isinstance(slug, str) and isinstance(label, str) and slug and label:
                models.append({"id": slug[:128], "name": label[:128]})
        return models[:100]

    async def disconnect(self, user_id: str) -> bool:
        parsed_user = self._user_uuid(user_id)
        refresh_token: str | None = None
        client_id: str | None = None
        async with self._factory() as session:
            async with session.begin():
                await self._set_user_scope(session, parsed_user)
                row = await session.scalar(
                    select(OpenAIPlanCredentialORM)
                    .where(OpenAIPlanCredentialORM.user_id == parsed_user)
                    .with_for_update()
                )
                if row is None:
                    return False
                try:
                    refresh_token = self._decrypt(parsed_user, "refresh", row.refresh_token_cipher)
                except ChatGPTPlanError:
                    _LOGGER.warning("chatgpt_plan_refresh_token_unreadable")
                client_id = row.client_id
                await session.delete(row)
        if refresh_token and client_id:
            try:
                await _revoke_refresh_token(client_id, refresh_token)
            except ChatGPTPlanError:
                _LOGGER.warning("chatgpt_plan_remote_revocation_unconfirmed")
        return True


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value or len(value) > 16_384:
        raise ChatGPTPlanError("A resposta OAuth está sem um campo obrigatório.")
    return value


def _valid_expires_in(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 60 <= value <= 86_400:
        raise ChatGPTPlanError("A resposta OAuth possui uma validade inválida.")
    return value


async def _discovery() -> dict[str, Any]:
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        async with client.stream("GET", f"{_AUTH_ORIGIN}{_DISCOVERY_PATH}") as response:
            if response.status_code != 200:
                raise ChatGPTPlanError(
                    "Não foi possível validar a infraestrutura de autenticação OpenAI."
                )
            raw = await _read_limited(response, 64 * 1024)
    if len(raw) > 64 * 1024:
        raise ChatGPTPlanError("Não foi possível validar a infraestrutura de autenticação OpenAI.")
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise ChatGPTPlanError("A descoberta OIDC retornou dados inválidos.") from exc
    if not isinstance(payload, dict):
        raise ChatGPTPlanError("A descoberta OIDC retornou dados inválidos.")
    if payload.get("issuer") != _ISSUER or payload.get("jwks_uri") != (
        f"{_AUTH_ORIGIN}/.well-known/jwks.json"
    ):
        raise ChatGPTPlanError("A configuração OIDC retornou uma origem inesperada.")
    return payload


async def validate_identity_token(
    token: str,
    *,
    client_id: str,
    expected_nonce: str | None = None,
) -> dict[str, Any]:
    global _JWKS_CACHE
    discovery = await _discovery()
    now = datetime.now(UTC).timestamp()
    jwks: list[dict[str, Any]]
    if _JWKS_CACHE and _JWKS_CACHE[0] > now:
        jwks = _JWKS_CACHE[1]
    else:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            async with client.stream("GET", discovery["jwks_uri"]) as response:
                if response.status_code != 200:
                    raise ChatGPTPlanError("Não foi possível obter as chaves de validação OpenAI.")
                raw = await _read_limited(response, 256 * 1024)
        if len(raw) > 256 * 1024:
            raise ChatGPTPlanError("Não foi possível obter as chaves de validação OpenAI.")
        try:
            keys = json.loads(raw)["keys"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ChatGPTPlanError("A resposta JWKS da OpenAI é inválida.") from exc
        if not isinstance(keys, list):
            raise ChatGPTPlanError("A resposta JWKS da OpenAI é inválida.")
        jwks = [item for item in keys if isinstance(item, dict)]
        _JWKS_CACHE = (now + 300.0, jwks)

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        matching = next(
            item for item in jwks if item.get("kid") == kid and item.get("kty") == "RSA"
        )
        key = jwt.PyJWK.from_dict(matching, algorithm="RS256").key
        claims = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=_ISSUER,
            options={"require": ["iss", "sub", "aud", "exp", "iat", "nonce"]},
            leeway=30,
        )
    except (jwt.PyJWTError, StopIteration, TypeError, ValueError) as exc:
        raise ChatGPTPlanError("O ID token ChatGPT não passou na validação criptográfica.") from exc
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise ChatGPTPlanError("O ID token não contém um identificador de conta válido.")
    if expected_nonce is not None:
        claim_nonce = claims.get("nonce")
        if not isinstance(claim_nonce, str) or not hmac.compare_digest(claim_nonce, expected_nonce):
            raise ChatGPTPlanError("A confirmação OAuth não corresponde à tentativa iniciada.")
    return claims


async def _token_request(data: dict[str, str]) -> dict[str, Any]:
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0, connect=5.0),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        async with client.stream(
            "POST",
            f"{_AUTH_ORIGIN}/api/accounts/oauth/token",
            data=data,
            headers={"Accept": "application/json"},
        ) as response:
            raw = await _read_limited(response, 64 * 1024)
            status_code = response.status_code
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise ChatGPTPlanError("A resposta OAuth está em formato inválido.") from exc
    if not isinstance(payload, dict):
        raise ChatGPTPlanError("A resposta OAuth está em formato inválido.")
    if status_code != 200:
        error = payload.get("error")
        if error in {"invalid_grant", "invalid_token"}:
            raise ChatGPTPlanError("invalid_grant: refresh token expirado ou revogado.")
        raise ChatGPTPlanError(f"OAuth token endpoint error (HTTP {status_code}).")
    return payload


async def _refresh_tokens(client_id: str, refresh_token: str) -> dict[str, Any]:
    return await _token_request(
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
            "resource": _API_ORIGIN,
        }
    )


async def _revoke_refresh_token(client_id: str, refresh_token: str) -> None:
    discovery = await _discovery()
    endpoint = discovery.get("revocation_endpoint")
    if not isinstance(endpoint, str) or not endpoint.startswith(f"{_AUTH_ORIGIN}/"):
        raise ChatGPTPlanError("O endpoint de revogação não é confiável.")
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        async with client.stream(
            "POST",
            endpoint,
            data={
                "token": refresh_token,
                "token_type_hint": "refresh_token",
                "client_id": client_id,
            },
        ) as response:
            await _read_limited(response, 16 * 1024)
            status_code = response.status_code
    if status_code != 200:
        raise ChatGPTPlanError(f"revocation failed (HTTP {status_code}).")


_store: ChatGPTPlanStore | None = None


def get_chatgpt_plan_store() -> ChatGPTPlanStore:
    global _store
    if _store is None:
        _store = ChatGPTPlanStore()
    return _store


__all__ = [
    "ChatGPTPlanError",
    "ChatGPTPlanStore",
    "get_chatgpt_plan_store",
    "validate_identity_token",
]
