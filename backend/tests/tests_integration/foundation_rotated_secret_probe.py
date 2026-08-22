"""Revalida, sem imprimir valores, que credenciais históricas foram invalidadas."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from redis import Redis

ROOT = Path(__file__).resolve().parents[3]
OLD_REDIS_COMMIT = "d3f590075eb972fc0d268d8251e20261f24f20a8"
OLD_REDIS_FILE = "REDIS_CLOUD_CONFIG.md"
OLD_NVIDIA_COMMITS = (
    "b812556bde3cc9b5bfb3dee7e909ee0d8055bf09",
    "d3f590075eb972fc0d268d8251e20261f24f20a8",
)
OLD_NVIDIA_FILE = "INFRASTRUCTURE_READY.md"


def current_env(name: str) -> str:
    env_path = ROOT / ".env"
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def git_file(commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def old_redis_auth() -> tuple[str, str]:
    content = git_file(OLD_REDIS_COMMIT, OLD_REDIS_FILE)
    match = re.search(r"curl\s+-u\s+([^\s`]+)", content)
    if match is None:
        raise RuntimeError("historical Redis auth pattern not found")
    username, separator, password = match.group(1).partition(":")
    if not separator or not username or not password:
        raise RuntimeError("historical Redis auth pair is incomplete")
    return username, password


def old_nvidia_key() -> str:
    for commit in OLD_NVIDIA_COMMITS:
        content = git_file(commit, OLD_NVIDIA_FILE)
        match = re.search(r"^NEGAO_NVIDIA_API_KEY=(\S+)$", content, re.MULTILINE)
        if match is not None and match.group(1):
            return match.group(1)
    raise RuntimeError("historical NVIDIA key pattern not found")


def test_old_redis() -> None:
    redis_url = current_env("NEGAO_REDIS_URL")
    username, password = old_redis_auth()
    parsed = urlsplit(redis_url)
    if not parsed.hostname:
        raise RuntimeError("current Redis host is unavailable")
    client = Redis(
        host=parsed.hostname,
        port=parsed.port or 6379,
        username=username,
        password=password,
        db=int(parsed.path.strip("/") or "0"),
        ssl=parsed.scheme == "rediss",
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    current_password = parsed.password or ""
    print(f"REDIS_OLD_CREDENTIAL_EQUALS_CURRENT={int(password == current_password)}")
    try:
        client.ping()
    except Exception:
        print("OLD_REDIS_CREDENTIAL=REJECTED")
    else:
        print("OLD_REDIS_CREDENTIAL=STILL_ACCEPTED")
    finally:
        client.close()


def test_old_nvidia() -> None:
    key = old_nvidia_key()
    current_key = current_env("NEGAO_NVIDIA_API_KEY")
    print(f"NVIDIA_OLD_CREDENTIAL_EQUALS_CURRENT={int(key == current_key)}")
    base_url = current_env("NEGAO_NVIDIA_BASE_URL").rstrip("/")
    response = httpx.get(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=8,
    )
    print(f"OLD_NVIDIA_CREDENTIAL_MODELS_STATUS={response.status_code}")


if __name__ == "__main__":
    test_old_redis()
    test_old_nvidia()
