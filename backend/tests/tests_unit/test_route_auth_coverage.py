"""Regressão: toda rota HTTP deve ser pública (allowlist explícita) ou exigir
API key — evita que um novo endpoint fique acessível sem autenticação por
omissão, como aconteceu antes desta correção (ver docs/sophie/CURRENT_STATE.md)."""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import create_app
from app.modules.security.router import require_authenticated_user, require_service_auth

_PUBLIC_ALLOWLIST = {
    ("GET", "/"),
    ("GET", "/healthz"),
    ("GET", "/health/live"),
    ("GET", "/readyz"),
    ("GET", "/health/ready"),
    ("GET", "/metrics"),
    ("GET", "/monitoring/metrics"),
    ("GET", "/events/health"),
    ("POST", "/security/login"),
    ("POST", "/security/register"),
}


def _requires_auth(route: APIRoute) -> bool:
    return any(
        dep.call in {require_authenticated_user, require_service_auth}
        for dep in route.dependant.dependencies
    )


def test_toda_rota_http_e_publica_ou_exige_api_key() -> None:
    app = create_app()
    unprotected: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            # WebSocketRoute (/ws, /ws/conversation, /ws/voice) autentica via
            # authenticate_ws() (ticket/api_key) — fora do escopo deste teste.
            # Rotas de docs/openapi são starlette.routing.Route puras, não
            # APIRoute, e já ficam desativadas em produção (settings.env).
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            key = (method, route.path)
            if key in _PUBLIC_ALLOWLIST:
                continue
            if not _requires_auth(route):
                unprotected.append(f"{method} {route.path}")
    assert not unprotected, (
        f"rotas HTTP sem autenticação e fora da allowlist pública: {sorted(unprotected)}"
    )
