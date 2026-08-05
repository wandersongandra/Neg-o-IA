"""Testes unitários do módulo voice — domain, VoiceService e WebSocket /ws/voice."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.modules.configuration.settings import Settings, get_settings
from app.modules.events.envelope import EventEnvelope
from app.modules.voice.application import VoiceService
from app.modules.voice.domain import (
    AudioResult,
    TranscriptionResult,
    VoiceUnavailableError,
)
from app.modules.voice.events import EVENT_VOICE_TRANSCRIPTION_COMPLETED
from app.modules.voice.infrastructure import FakeSTTAdapter, FakeTTSAdapter
from app.modules.voice.router import router as voice_router
from app.modules.voice.router import voice_ws_router

API_KEY = get_settings().api_key


class _CapturingBus:
    """Event bus fake que captura os envelopes publicados."""

    def __init__(self) -> None:
        self.envelopes: list[EventEnvelope] = []

    async def publish_event(self, envelope: EventEnvelope) -> None:
        self.envelopes.append(envelope)


class _FakeVoiceService:
    """VoiceService fake para o WebSocket — transcribe/synthesize determinísticos."""

    async def transcribe(self, audio_bytes: bytes, *, content_type: str) -> TranscriptionResult:
        return TranscriptionResult(text="olá", language="pt", duration_seconds=0.5)

    async def synthesize(self, text: str) -> AudioResult:
        return AudioResult(data=b"fake-mp3", content_type="audio/mpeg")


@pytest.mark.asyncio
async def test_fake_stt_retorna_valores_sem_rede() -> None:
    adapter = FakeSTTAdapter(stt_result="oi", language="pt", duration_seconds=2.0)

    result = await adapter.transcribe(b"audio", content_type="audio/webm")

    assert result.text == "oi"
    assert result.language == "pt"
    assert result.duration_seconds == 2.0


@pytest.mark.asyncio
async def test_fake_tts_retorna_valores_sem_rede() -> None:
    adapter = FakeTTSAdapter(tts_bytes=b"mp3-fake")

    result = await adapter.synthesize("oi")

    assert result.data == b"mp3-fake"
    assert result.content_type == "audio/mpeg"


@pytest.mark.asyncio
async def test_service_transcribe_publica_evento_e_retorna_texto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bus = _CapturingBus()
    monkeypatch.setattr("app.modules.events.application.get_event_bus_service", lambda: bus)
    service = VoiceService(
        FakeSTTAdapter(),
        FakeTTSAdapter(),
        settings=Settings(nvidia_api_key="test-key"),
    )

    result = await service.transcribe(b"audio", content_type="audio/webm")

    assert result.text == "texto"
    assert len(bus.envelopes) == 1
    envelope = bus.envelopes[0]
    assert envelope.type == EVENT_VOICE_TRANSCRIPTION_COMPLETED
    assert envelope.producer == "voice"
    assert envelope.payload["text"] == "texto"
    assert envelope.payload["duration_seconds"] == 1.5


@pytest.mark.asyncio
async def test_service_synthesize_retorna_audio() -> None:
    service = VoiceService(FakeSTTAdapter(), FakeTTSAdapter())

    result = await service.synthesize("oi")

    assert result.data == b"fake-mp3"
    assert result.content_type == "audio/mpeg"


@pytest.mark.asyncio
async def test_service_stt_indisponivel_sem_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.modules.configuration.settings as settings_module

    settings = settings_module.get_settings()
    monkeypatch.setattr(settings, "nvidia_api_key", "")
    service = VoiceService(FakeSTTAdapter(), FakeTTSAdapter())

    with pytest.raises(VoiceUnavailableError, match="NEGAO_NVIDIA_API_KEY"):
        await service.transcribe(b"audio", content_type="audio/webm")


def test_ws_voice_protocol_transcreve_e_sintetiza(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.voice.application.get_voice_service",
        lambda: _FakeVoiceService(),
    )
    application = FastAPI()
    application.include_router(voice_router)
    application.include_router(voice_ws_router)

    with TestClient(application) as client:
        with client.websocket_connect(f"/ws/voice?api_key={API_KEY}") as ws:
            ws.send_json({"type": "start", "session_id": "sess-1"})
            ws.send_bytes(b"audio-bytes")
            ws.send_json({"type": "end"})

            transcript = ws.receive_json()
            assert transcript["type"] == "transcript"
            assert transcript["text"] == "olá"
            assert transcript["session_id"] == "sess-1"

            ws.send_json({"type": "speak", "text": "oi"})
            assert ws.receive_bytes() == b"fake-mp3"
            meta = ws.receive_json()
            assert meta["type"] == "audio"
            assert meta["content_type"] == "audio/mpeg"
            assert meta["bytes"] == len(b"fake-mp3")

            ws.send_json({"type": "start", "session_id": None})
            ws.send_json({"type": "end"})
            error = ws.receive_json()
            assert error["type"] == "error"

            ws.close()
