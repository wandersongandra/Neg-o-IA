"""Contratos do módulo voice — domain (framework-free).

Responsabilidade única: entrada de fala (ASR/STT) e saída de voz (TTS),
com sessões de voz via WebSocket. Faz transcrição e síntese;
NÃO interpreta o texto (isso é do Reasoning).
Aqui vivem os contratos (Protocols), os resultados imutáveis e os erros
do domínio; não há rede, HTTP ou chamadas externas nesta camada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TranscriptionResult:
    """Resultado da transcrição de um áudio (texto + metadados)."""

    text: str
    language: str | None = None
    duration_seconds: float | None = None


@dataclass(frozen=True)
class AudioResult:
    """Áudio sintetizado (bytes prontos para streaming)."""

    data: bytes
    content_type: str


class STTAdapter(Protocol):
    """Porta de reconhecimento de fala (speech-to-text)."""

    async def transcribe(self, audio_bytes: bytes, *, content_type: str) -> TranscriptionResult: ...


class TTSAdapter(Protocol):
    """Porta de síntese de fala (text-to-speech)."""

    async def synthesize(self, text: str) -> AudioResult: ...


class VoicePort(Protocol):
    """Porta pública do Voice (ASR/TTS) — implementada pelo VoiceService."""

    async def transcribe(self, audio_bytes: bytes, *, content_type: str) -> TranscriptionResult: ...

    async def synthesize(self, text: str) -> AudioResult: ...


class VoiceError(Exception):
    """Erro base do módulo voice."""


class VoiceUnavailableError(VoiceError):
    """Serviço de voz indisponível por configuração (ex.: API key ausente)."""


class VoiceProviderError(VoiceError):
    """Falha do provedor externo de STT/TTS."""
