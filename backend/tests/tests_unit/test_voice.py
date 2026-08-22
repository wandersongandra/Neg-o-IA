"""Testes unitários do módulo voice — domain, VoiceService e WebSocket /ws/voice."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.modules.configuration.settings import Settings, get_settings
from app.modules.conversation.application import ChatResult
from app.modules.events.envelope import EventEnvelope
from app.modules.security.domain import AuthResult
from app.modules.voice.application import VoiceService
from app.modules.voice.domain import (
    AudioResult,
    TranscriptionResult,
    VoiceProtocolError,
    VoiceSessionState,
    VoiceUnavailableError,
    transition_voice_state,
)
from app.modules.voice.events import EVENT_VOICE_TRANSCRIPTION_COMPLETED
from app.modules.voice.infrastructure import FakeSTTAdapter, FakeTTSAdapter
from app.modules.voice.router import (
    _handle_audio_chunk,
    _handle_turn_start,
    _parse_protocol_message,
    _WsVoiceSession,
    voice_ws_router,
)
from app.modules.voice.router import router as voice_router


class _CapturingBus:
    """Event bus fake que captura os envelopes publicados."""

    def __init__(self) -> None:
        self.envelopes: list[EventEnvelope] = []

    async def publish_event(self, envelope: EventEnvelope) -> None:
        self.envelopes.append(envelope)


class _FakeVoiceService:
    """VoiceService fake para o WebSocket — sem rede e sem persistência."""

    def __init__(self, transcripts: list[str] | None = None) -> None:
        self.transcripts = transcripts or ["olá"]
        self.transcribe_calls: list[tuple[bytes, str]] = []
        self.synthesize_calls: list[str] = []

    async def transcribe(self, audio_bytes: bytes, *, content_type: str) -> TranscriptionResult:
        self.transcribe_calls.append((audio_bytes, content_type))
        text = self.transcripts[min(len(self.transcribe_calls) - 1, len(self.transcripts) - 1)]
        return TranscriptionResult(text=text, language="pt", duration_seconds=0.5)

    async def synthesize(self, text: str) -> AudioResult:
        self.synthesize_calls.append(text)
        return AudioResult(data=b"fake-mp3", content_type="audio/mpeg")


class _FakeConversationService:
    """ConversationService fake que registra sessão e preserva contexto entre turnos."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    async def owns_session(self, session_id: str, user_id: str) -> bool:
        return session_id == "sess-1" and user_id == "user-test"

    async def chat(self, session_id: str, text: str, *, user_id: str | None = None) -> ChatResult:
        self.calls.append((session_id, text, user_id))
        response = (
            "Você acabou de dizer teste-abc."
            if "Qual nome" in text
            else "Entendi, vou lembrar nesta sessão."
        )
        return ChatResult(
            text=response,
            model="fake-brain",
            latency_ms=1,
            fallback_used=False,
            cached=False,
        )


class _FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []
        self.close_code: int | None = None

    async def send_json(self, message: dict[str, object]) -> None:
        self.messages.append(message)

    async def close(self, code: int, reason: str = "") -> None:
        self.close_code = code


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


def test_voice_state_machine_rejeita_transicao_invalida() -> None:
    assert (
        transition_voice_state(VoiceSessionState.CONNECTED, "session.start")
        is VoiceSessionState.SESSION_READY
    )
    assert (
        transition_voice_state(VoiceSessionState.SESSION_READY, "turn.start")
        is VoiceSessionState.LISTENING
    )
    with pytest.raises(VoiceProtocolError, match="transição inválida"):
        transition_voice_state(VoiceSessionState.CONNECTED, "turn.start")


def test_voice_protocol_rejeita_versao_desconhecida() -> None:
    with pytest.raises(VoiceProtocolError, match="unsupported protocol version"):
        _parse_protocol_message('{"type":"voice.session.start","version":99}')


@pytest.mark.asyncio
async def test_voice_chunk_excede_limite_e_fecha_com_policy_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "voice_max_chunk_bytes", 2)
    session = _WsVoiceSession(
        auth=AuthResult(authenticated=True, principal="user-test", session_id="sess-1"),
        state=VoiceSessionState.LISTENING,
    )
    ws = _FakeWebSocket()

    await _handle_audio_chunk(ws, session, b"123")

    assert ws.messages[0]["code"] == "AUDIO_CHUNK_TOO_LARGE"
    assert ws.close_code == 1009
    assert session.audio == bytearray()


@pytest.mark.asyncio
async def test_voice_turn_rejeita_formato_nao_declarado() -> None:
    session = _WsVoiceSession(
        auth=AuthResult(authenticated=True, principal="user-test", session_id="sess-1"),
        state=VoiceSessionState.SESSION_READY,
    )
    with pytest.raises(VoiceProtocolError, match="unsupported audio format"):
        await _handle_turn_start(
            _FakeWebSocket(),
            session,
            {"format": "audio/wav", "interaction_id": "interaction-1"},
        )


def test_ws_voice_exige_ticket_antes_do_accept() -> None:
    application = FastAPI()
    application.include_router(voice_ws_router)

    with TestClient(application) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/voice"):
                pass

    assert exc_info.value.code == 1008


def test_voice_http_routes_exigem_api_key() -> None:
    application = FastAPI()
    application.include_router(voice_router)

    with TestClient(application) as client:
        status_response = client.get("/voice/status")
        tts_response = client.post("/voice/synthesize", json={"text": "oi"})

    assert status_response.status_code == 401
    assert tts_response.status_code == 401


def test_ws_voice_v1_integra_conversa_e_preserva_sessao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    voice_service = _FakeVoiceService(
        ["Meu nome temporário é teste-abc.", "Qual nome eu acabei de dizer?"]
    )
    conversation_service = _FakeConversationService()
    monkeypatch.setattr(
        "app.modules.voice.router._get_voice_service",
        lambda: voice_service,
    )
    monkeypatch.setattr(
        "app.modules.voice.router.get_conversation_service",
        lambda: conversation_service,
    )

    async def authenticate_voice_ticket(*_args: object, **_kwargs: object) -> AuthResult:
        return AuthResult(
            authenticated=True,
            principal="user-test",
            purpose="voice",
            session_id="sess-1",
        )

    monkeypatch.setattr("app.modules.voice.router.authenticate_ws", authenticate_voice_ticket)
    application = FastAPI()
    application.include_router(voice_ws_router)

    with TestClient(application) as client:
        with client.websocket_connect("/ws/voice?ticket=voice-ticket") as ws:
            ws.send_json(
                {
                    "type": "voice.session.start",
                    "version": 1,
                    "session_id": "sess-1",
                    "interaction_id": "interaction-1",
                }
            )
            assert ws.receive_json()["type"] == "voice.session.started"
            assert ws.receive_json()["state"] == "SESSION_READY"

            def run_turn(interaction_id: str, expected_transcript: str) -> None:
                ws.send_json(
                    {
                        "type": "voice.turn.start",
                        "version": 1,
                        "format": "audio/webm",
                        "interaction_id": interaction_id,
                    }
                )
                assert ws.receive_json()["state"] == "LISTENING"
                ws.send_bytes(b"audio-bytes")
                ws.send_json(
                    {
                        "type": "voice.turn.end",
                        "version": 1,
                    }
                )

                assert ws.receive_json()["state"] == "TRANSCRIBING"
                transcript = ws.receive_json()
                assert transcript["type"] == "voice.transcript.final"
                assert transcript["text"] == expected_transcript
                assert ws.receive_json()["state"] == "THINKING"
                assert ws.receive_json()["type"] == "voice.response.started"
                response = ws.receive_json()
                assert response["type"] == "voice.response.text"
                assert ws.receive_json()["state"] == "SYNTHESIZING"
                audio_meta = ws.receive_json()
                assert audio_meta["type"] == "voice.response.audio"
                assert audio_meta["format"] == "audio/mpeg"
                assert ws.receive_bytes() == b"fake-mp3"
                assert ws.receive_json()["type"] == "voice.response.completed"
                assert ws.receive_json()["state"] == "IDLE"

            run_turn("interaction-1", "Meu nome temporário é teste-abc.")
            run_turn("interaction-2", "Qual nome eu acabei de dizer?")

            ws.send_json(
                {
                    "type": "voice.session.stop",
                    "version": 1,
                }
            )
            stopped = ws.receive_json()
            assert stopped["type"] == "voice.session.stopped"

    assert [call[0] for call in conversation_service.calls] == ["sess-1", "sess-1"]
    assert [call[2] for call in conversation_service.calls] == ["user-test", "user-test"]
    assert len(voice_service.transcribe_calls) == 2
    assert all(content_type == "audio/webm" for _, content_type in voice_service.transcribe_calls)
    assert len(voice_service.synthesize_calls) == 2
