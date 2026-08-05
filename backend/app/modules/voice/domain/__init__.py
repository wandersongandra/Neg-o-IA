"""Contratos do módulo voice — domain (framework-free).

Responsabilidade única: entrada de fala (ASR) e saída de voz (TTS),
com VAD e sessões de voz via WebSocket. Faz transcrição e síntese;
NÃO interpreta o texto (isso é do Reasoning).
"""

from __future__ import annotations

from typing import Protocol


class VoicePort(Protocol):
    """Porta pública do Voice (ASR/TTS)."""

    async def transcribe(self, audio_bytes: bytes) -> str: ...

    async def synthesize(self, text: str) -> bytes: ...
