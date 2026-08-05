"""Contrato de eventos do módulo voice — catálogo v1 (Event Bus).

Producer deste módulo: "voice".
"""

from __future__ import annotations

from typing import Final

EVENT_VERSION = 1

EVENT_VOICE_TRANSCRIPTION_COMPLETED: Final[str] = "voice.transcription.completed"
EVENT_VOICE_SYNTHESIS_COMPLETED: Final[str] = "voice.synthesis.completed"
EVENT_VOICE_UNAVAILABLE: Final[str] = "voice.unavailable"

EVENT_CATALOG: Final[dict[str, str]] = {
    EVENT_VOICE_TRANSCRIPTION_COMPLETED: (
        "Transcrição de fala concluída (STT) com o texto e a duração do áudio"
    ),
    EVENT_VOICE_SYNTHESIS_COMPLETED: (
        "Síntese de fala concluída (TTS) com o content-type e o tamanho do áudio"
    ),
    EVENT_VOICE_UNAVAILABLE: (
        "STT/TTS indisponível no momento (ex.: NEGAO_NVIDIA_API_KEY não configurada)"
    ),
}

PUBLISHED: Final[frozenset[str]] = frozenset(
    {
        EVENT_VOICE_TRANSCRIPTION_COMPLETED,
        EVENT_VOICE_SYNTHESIS_COMPLETED,
        EVENT_VOICE_UNAVAILABLE,
    }
)

CONSUMED: Final[frozenset[str]] = frozenset(
    {
        "brain.response.ready",
        "voice.tts.requested",
    }
)

PRODUCER: Final[str] = "voice"
