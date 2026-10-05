"""High-confidence detection of credentials that should not be auto-persisted."""

from __future__ import annotations

import re

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", re.IGNORECASE),
    ),
    (
        "authorization_bearer",
        re.compile(r"\bAuthorization\s*:\s*Bearer\s+[^\s]{16,}", re.IGNORECASE),
    ),
    (
        "bearer_token",
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE),
    ),
    (
        "jwt",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
        ),
    ),
    (
        "known_token_prefix",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
            r"sk-[A-Za-z0-9_-]{20,}|nvapi-[A-Za-z0-9_-]{20,})\b"
        ),
    ),
    (
        "credential_uri",
        re.compile(
            r"\b(?:postgres(?:ql)?|redis|mysql|mongodb(?:\+srv)?)://"
            r"[^:\s/]+:[^@\s/]{6,}@",
            re.IGNORECASE,
        ),
    ),
    (
        "credential_assignment",
        re.compile(
            r"\b(?:password|passwd|api[_-]?key|secret|access[_-]?token)\b"
            r"\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{16,}",
            re.IGNORECASE,
        ),
    ),
)


def likely_secret_kind(content: str) -> str | None:
    """Return a coarse category without returning or logging the matched secret."""
    for kind, pattern in _PATTERNS:
        if pattern.search(content):
            return kind
    return None


def contains_likely_secret(content: str) -> bool:
    return likely_secret_kind(content) is not None
