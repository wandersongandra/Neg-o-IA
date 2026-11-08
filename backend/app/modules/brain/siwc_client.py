"""Local Sign in with ChatGPT client for the self-hosted Ultron instance."""

from __future__ import annotations

import base64
import getpass
import hashlib
import hmac
import http.server
import json
import secrets
import time
import urllib.parse
import webbrowser
from typing import Any

import httpx
import jwt

AUTH_ORIGIN = "https://auth.openai.com"
API_RESOURCE = "https://api.openai.com/v1"
JWKS_URL = f"{AUTH_ORIGIN}/.well-known/jwks.json"
ISSUER = AUTH_ORIGIN
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"


class SiwcError(RuntimeError):
    """A local ChatGPT sign-in or secure upload failed."""


def _read_limited(response: httpx.Response, limit: int) -> bytes:
    declared = response.headers.get("content-length")
    if declared:
        try:
            if int(declared) > limit:
                raise SiwcError("A resposta da OpenAI excedeu o limite permitido.")
        except ValueError:
            pass
    parts: list[bytes] = []
    total = 0
    for part in response.iter_bytes():
        total += len(part)
        if total > limit:
            raise SiwcError("A resposta da OpenAI excedeu o limite permitido.")
        parts.append(part)
    return b"".join(parts)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _safe_api_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    local_http = parsed.scheme == "http" and parsed.hostname in {
        "127.0.0.1",
        "localhost",
        "::1",
    }
    if parsed.scheme != "https" and not local_http:
        raise SiwcError("A API do agente deve usar HTTPS (HTTP só é permitido em loopback local).")
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise SiwcError("A URL da API do agente é inválida.")
    return f"{parsed.scheme}://{parsed.netloc}"


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if len(self.path) > 8192:
            self.send_error(414)
            return
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/auth/callback":
            self.send_error(404)
            return
        try:
            self.server.callback = urllib.parse.parse_qs(  # type: ignore[attr-defined]
                parsed.query, keep_blank_values=True, max_num_fields=20
            )
        except ValueError:
            self.send_error(400)
            return
        content = (
            "<!doctype html><meta charset=utf-8><title>Ultron</title>"
            "<main style='font:16px system-ui;max-width:34rem;margin:12vh auto;padding:2rem'>"
            "<h1>Autorização recebida</h1>"
            "<p>Volte ao terminal da Ultron para concluir a conexão.</p></main>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        return


def _complete_oauth(
    code: str,
    *,
    client_id: str,
    redirect_uri: str,
    verifier: str,
) -> dict[str, Any]:
    with httpx.Client(
        timeout=httpx.Timeout(20.0, connect=5.0),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        with client.stream(
            "POST",
            f"{AUTH_ORIGIN}/api/accounts/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": redirect_uri,
                "resource": API_RESOURCE,
            },
            headers={"Accept": "application/json"},
        ) as response:
            payload_bytes = _read_limited(response, 64 * 1024)
            status_code = response.status_code
    if status_code != 200:
        raise SiwcError("A OpenAI não aceitou a troca do código OAuth.")
    try:
        payload = json.loads(payload_bytes)
    except ValueError as exc:
        raise SiwcError("A resposta OAuth recebida está inválida.") from exc
    if not isinstance(payload, dict):
        raise SiwcError("A resposta OAuth recebida está inválida.")
    return payload


def _validate_identity_token(
    token: str,
    *,
    client_id: str,
    nonce: str,
) -> dict[str, Any]:
    with httpx.Client(
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        with client.stream("GET", JWKS_URL) as response:
            jwks_bytes = _read_limited(response, 256 * 1024)
            status_code = response.status_code
    if status_code != 200:
        raise SiwcError("Não foi possível validar a assinatura do ID token.")
    try:
        key_entries = json.loads(jwks_bytes)["keys"]
        kid = jwt.get_unverified_header(token).get("kid")
        jwk = next(
            entry
            for entry in key_entries
            if isinstance(entry, dict) and entry.get("kid") == kid and entry.get("kty") == "RSA"
        )
        claims = jwt.decode(
            token,
            key=jwt.PyJWK.from_dict(jwk, algorithm="RS256").key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=ISSUER,
            options={"require": ["iss", "sub", "aud", "exp", "iat", "nonce"]},
            leeway=30,
        )
    except (ValueError, TypeError, KeyError, StopIteration, jwt.PyJWTError) as exc:
        raise SiwcError("O ID token não passou na validação de identidade.") from exc
    claim_nonce = claims.get("nonce")
    if (
        not isinstance(claim_nonce, str)
        or not hmac.compare_digest(claim_nonce, nonce)
        or not isinstance(claims.get("sub"), str)
    ):
        raise SiwcError("O ID token não corresponde a esta tentativa de autorização.")
    return claims


def connect_chatgpt_plan(*, api_url: str, username: str | None = None) -> int:
    api = _safe_api_url(api_url)
    origin = urllib.parse.urlsplit(api).geturl()
    headers_origin = {"Origin": origin, "Accept": "application/json"}
    selected_username = username or input("Usuário da Ultron: ").strip()
    password = getpass.getpass("Senha da Ultron (não será salva): ")
    if not selected_username or not password:
        raise SiwcError("Usuário e senha da Ultron são obrigatórios.")

    with httpx.Client(
        timeout=httpx.Timeout(20.0, connect=5.0),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        login = client.post(
            f"{api}/api/auth/login",
            headers=headers_origin,
            json={
                "username": selected_username,
                "password": password,
                "device_name": "ChatGPT plan authorization",
                "device_type": "cli",
            },
        )
        password = ""
        if login.status_code != 200:
            raise SiwcError("Não foi possível autenticar na Ultron.")
        # The frontend's HttpOnly cookie stays inside this client's cookie jar.
        headers = dict(headers_origin)
        try:
            return _finish_chatgpt_plan_connection(client, api, headers)
        finally:
            _logout(client, api, headers)


def _finish_chatgpt_plan_connection(
    client: httpx.Client,
    api: str,
    headers: dict[str, str],
) -> int:
    status_response = client.get(f"{api}/api/proxy/brain/chatgpt-plan/status", headers=headers)
    if status_response.status_code != 200:
        raise SiwcError("Não foi possível obter a identidade segura desta instalação.")
    try:
        host_id = status_response.json()["host_id"]
        existing_client_id = status_response.json().get("client_id")
    except (ValueError, KeyError, TypeError) as exc:
        raise SiwcError("O status da instalação não trouxe o host ID OAuth.") from exc
    if existing_client_id is not None and (
        not isinstance(existing_client_id, str) or not existing_client_id.startswith("oaiapp_")
    ):
        raise SiwcError("A conexão existente retornou um client ID inválido.")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    try:
        server = http.server.HTTPServer(("127.0.0.1", 0), _CallbackHandler)
    except OSError as exc:
        raise SiwcError("Não foi possível iniciar o callback OAuth local.") from exc
    redirect_uri = f"http://127.0.0.1:{server.server_port}/auth/callback"
    server.timeout = 1.0
    server.callback = None  # type: ignore[attr-defined]
    params = {
        "client_id": existing_client_id or "dynamic_agent_client",
        "ext_agent_host_id": host_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "resource": API_RESOURCE,
        "state": state,
        "nonce": nonce,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    if existing_client_id is None:
        params["agent_name_hint"] = "Ultron — Neg-o-IA"
    authorization_url = f"{AUTH_ORIGIN}/api/accounts/authorize?{urllib.parse.urlencode(params)}"
    print("A autorização expira em cinco minutos. Não compartilhe nem copie tokens.")
    if not webbrowser.open(authorization_url):
        print(authorization_url)
    deadline = time.monotonic() + 300
    try:
        while time.monotonic() < deadline and server.callback is None:  # type: ignore[attr-defined]
            server.handle_request()
    finally:
        server.server_close()
    callback = server.callback  # type: ignore[attr-defined]
    if not isinstance(callback, dict):
        raise SiwcError("O login OAuth expirou sem retorno do navegador.")
    callback_state = callback.get("state", [""])[0]
    if not isinstance(callback_state, str) or not hmac.compare_digest(callback_state, state):
        raise SiwcError("O estado OAuth não corresponde à tentativa iniciada.")
    if callback.get("error"):
        raise SiwcError("A autorização do plano ChatGPT foi recusada ou cancelada.")

    code = callback.get("code", [""])[0]
    client_id = callback.get("client_id", [""])[0]
    if not code:
        raise SiwcError("A OpenAI não retornou um código OAuth válido.")
    if client_id and existing_client_id and client_id != existing_client_id:
        raise SiwcError("A OpenAI retornou um client ID diferente da conexão existente.")
    issued_client_id = client_id or existing_client_id
    if not isinstance(issued_client_id, str) or not issued_client_id.startswith("oaiapp_"):
        raise SiwcError("A OpenAI não retornou um registro de cliente válido.")
    token_payload = _complete_oauth(
        code,
        client_id=issued_client_id,
        redirect_uri=redirect_uri,
        verifier=verifier,
    )
    scopes = str(token_payload.get("scope", "")).split()
    if "chatgpt.tokens.use.direct" not in scopes or "resource.invoke" not in scopes:
        raise SiwcError("O consentimento não autorizou o uso do plano para inferência.")
    id_token = token_payload.get("id_token")
    if not isinstance(id_token, str):
        raise SiwcError("A OpenAI não retornou um ID token para validar a conta.")
    claims = _validate_identity_token(id_token, client_id=issued_client_id, nonce=nonce)
    expires_in = token_payload.get("expires_in")
    if (
        isinstance(expires_in, bool)
        or not isinstance(expires_in, int)
        or not 60 <= expires_in <= 86_400
    ):
        raise SiwcError("A resposta OAuth retornou validade inválida.")

    body = {
        "client_id": issued_client_id,
        "host_id": host_id,
        "access_token": token_payload.get("access_token"),
        "refresh_token": token_payload.get("refresh_token"),
        "id_token": id_token,
        "nonce": nonce,
        "scopes": scopes,
        "expires_in": expires_in,
    }
    result = client.post(
        f"{api}/api/proxy/brain/chatgpt-plan/credentials",
        headers=headers,
        json=body,
    )
    if result.status_code != 204:
        raise SiwcError("A Ultron não conseguiu armazenar as credenciais autorizadas.")
    print(f"Plano conectado à conta ChatGPT {claims.get('email') or '(e-mail indisponível)'}.")
    print(
        "As credenciais ficaram apenas na memória local durante o envio e foram cifradas no banco."
    )
    return 0


def _logout(client: httpx.Client, api: str, headers: dict[str, str]) -> None:
    try:
        client.post(f"{api}/api/auth/logout", headers=headers)
    except httpx.HTTPError:
        return


__all__ = ["SiwcError", "connect_chatgpt_plan"]
