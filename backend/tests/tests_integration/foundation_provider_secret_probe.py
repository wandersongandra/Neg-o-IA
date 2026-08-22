"""Valida credenciais locais sem imprimir valores sensíveis."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import cast

import httpx
from redis.asyncio import Redis


def _env_value(name: str) -> str:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


async def main() -> None:
    redis_url = _env_value("NEGAO_REDIS_URL")
    redis_client = Redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
    try:
        await redis_client.ping()
        print("REDIS_ENV_CREDENTIAL_PING=SUCCESS")
        whoami = await redis_client.execute_command("ACL", "WHOAMI")
        print(f"REDIS_ENV_CREDENTIAL_WHOAMI={whoami}")
        acl_user = await redis_client.execute_command("ACL", "GETUSER", "default")
        acl_text = " ".join(
            item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item)
            for item in acl_user
        )
        print(f"REDIS_ENV_ACL_ADMIN_CATEGORY={int('+@admin' in acl_text)}")
    finally:
        close = cast(Callable[[], Awaitable[None]], redis_client.aclose)  # type: ignore[attr-defined]
        await close()

    nvidia_key = _env_value("NEGAO_NVIDIA_API_KEY")
    nvidia_base_url = _env_value("NEGAO_NVIDIA_BASE_URL").rstrip("/")
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get(
            f"{nvidia_base_url}/models",
            headers={"Authorization": f"Bearer {nvidia_key}"},
        )
    print(f"NVIDIA_ENV_CREDENTIAL_MODELS_STATUS={response.status_code}")


if __name__ == "__main__":
    asyncio.run(main())
