"""Contratos do módulo voice — domain (framework-free).

Responsabilidade única: entrada de fala (ASR/STT) e saída de voz (TTS),
com sessões de voz via WebSocket. Faz transcrição e síntese;
NÃO interpreta o texto (isso é do Reasoning).
Aqui vivem os contratos (Protocols), os resultados imutáveis e os erros
do domínio; não há rede, HTTP ou chamadas externas nesta camada.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
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


class VoiceSessionState(StrEnum):
    """Estados observáveis da máquina de sessão do protocolo Voice V1."""

    CONNECTED = "CONNECTED"
    SESSION_READY = "SESSION_READY"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    SYNTHESIZING = "SYNTHESIZING"
    RESPONDING = "RESPONDING"
    IDLE = "IDLE"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


class VoiceProtocolError(VoiceError):
    """Mensagem ou transição inválida no protocolo Voice V1."""


_TRANSITIONS: dict[VoiceSessionState, dict[str, VoiceSessionState]] = {
    VoiceSessionState.CONNECTED: {
        "session.start": VoiceSessionState.SESSION_READY,
        "session.stop": VoiceSessionState.CLOSED,
        "error": VoiceSessionState.ERROR,
    },
    VoiceSessionState.SESSION_READY: {
        "turn.start": VoiceSessionState.LISTENING,
        "session.stop": VoiceSessionState.CLOSED,
        "error": VoiceSessionState.ERROR,
    },
    VoiceSessionState.LISTENING: {
        "turn.end": VoiceSessionState.TRANSCRIBING,
        "session.stop": VoiceSessionState.CLOSED,
        "error": VoiceSessionState.ERROR,
    },
    VoiceSessionState.TRANSCRIBING: {
        "transcript.final": VoiceSessionState.THINKING,
        "turn.error": VoiceSessionState.IDLE,
        "session.stop": VoiceSessionState.CLOSED,
        "error": VoiceSessionState.ERROR,
    },
    VoiceSessionState.THINKING: {
        "response.started": VoiceSessionState.THINKING,
        "response.text": VoiceSessionState.SYNTHESIZING,
        "turn.error": VoiceSessionState.IDLE,
        "session.stop": VoiceSessionState.CLOSED,
        "error": VoiceSessionState.ERROR,
    },
    VoiceSessionState.SYNTHESIZING: {
        "response.audio": VoiceSessionState.RESPONDING,
        "turn.error": VoiceSessionState.IDLE,
        "session.stop": VoiceSessionState.CLOSED,
        "error": VoiceSessionState.ERROR,
    },
    VoiceSessionState.RESPONDING: {
        "response.completed": VoiceSessionState.IDLE,
        "turn.error": VoiceSessionState.IDLE,
        "session.stop": VoiceSessionState.CLOSED,
        "error": VoiceSessionState.ERROR,
    },
    VoiceSessionState.IDLE: {
        "turn.start": VoiceSessionState.LISTENING,
        "session.stop": VoiceSessionState.CLOSED,
        "error": VoiceSessionState.ERROR,
    },
    VoiceSessionState.ERROR: {
        "recover": VoiceSessionState.IDLE,
        "session.stop": VoiceSessionState.CLOSED,
    },
    VoiceSessionState.CLOSED: {},
}


def transition_voice_state(state: VoiceSessionState, event: str) -> VoiceSessionState:
    """Aplica uma transição explícita e rejeita eventos fora de ordem."""
    try:
        return _TRANSITIONS[state][event]
    except KeyError as exc:
        raise VoiceProtocolError(f"transição inválida: {state.value} + {event}") from exc
