"""Camada de aplicação do módulo voice — VoiceService (facade).

Orquestra os adapters de STT/TTS e publica os eventos de contrato de forma
best-effort: falha de publicação nunca quebra a transcrição/síntese.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.modules.configuration.settings import Settings, get_settings
from app.modules.events.envelope import build_envelope
from app.modules.voice.domain import (
    AudioResult,
    STTAdapter,
    TranscriptionResult,
    TTSAdapter,
    VoiceUnavailableError,
)
from app.modules.voice.events import (
    EVENT_VOICE_SYNTHESIS_COMPLETED,
    EVENT_VOICE_TRANSCRIPTION_COMPLETED,
    EVENT_VOICE_UNAVAILABLE,
    PRODUCER,
)

logger = structlog.get_logger("negao.voice.application")

_voice_service: VoiceService | None = None


class VoiceService:
    """Facade pública do Voice: transcreve áudio (STT) e sintetiza fala (TTS)."""

    def __init__(
        self,
        stt_adapter: STTAdapter,
        tts_adapter: TTSAdapter,
        settings: Settings | None = None,
    ) -> None:
        self._stt_adapter = stt_adapter
        self._tts_adapter = tts_adapter
        self._settings = settings

    def _resolve_settings(self) -> Settings:
        return self._settings or get_settings()

    async def transcribe(self, audio_bytes: bytes, *, content_type: str) -> TranscriptionResult:
        if not self._resolve_settings().nvidia_api_key:
            await self._publish(EVENT_VOICE_UNAVAILABLE, {"reason": "stt_not_configured"})
            raise VoiceUnavailableError("STT não configurado — defina NEGAO_NVIDIA_API_KEY")
        result = await self._stt_adapter.transcribe(audio_bytes, content_type=content_type)
        await self._publish(
            EVENT_VOICE_TRANSCRIPTION_COMPLETED,
            {
                "text": result.text,
                "language": result.language,
                "duration_seconds": result.duration_seconds,
            },
        )
        return result

    async def synthesize(self, text: str) -> AudioResult:
        result = await self._tts_adapter.synthesize(text)
        await self._publish(
            EVENT_VOICE_SYNTHESIS_COMPLETED,
            {"content_type": result.content_type, "bytes": len(result.data)},
        )
        return result

    async def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            service = get_event_bus_service()
            await service.publish_event(build_envelope(event_type, PRODUCER, payload))
        except Exception as exc:
            logger.warning("voice_event_publish_failed", event_type=event_type, error=str(exc))


def get_voice_service() -> VoiceService:
    """Singleton do VoiceService com os adapters reais (NVIDIA STT + edge-tts)."""
    global _voice_service
    if _voice_service is None:
        from app.modules.voice.infrastructure import EdgeTTSAdapter, NvidiaTranscriptionAdapter

        _voice_service = VoiceService(
            stt_adapter=NvidiaTranscriptionAdapter(),
            tts_adapter=EdgeTTSAdapter(),
        )
    return _voice_service
