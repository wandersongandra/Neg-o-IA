"""Adaptadores do módulo voice — STT (NVIDIA NIM) e TTS (edge-tts).

`NvidiaTranscriptionAdapter` e `EdgeTTSAdapter` são os adapters reais;
`FakeSTTAdapter` e `FakeTTSAdapter` existem para testes e nunca tocam rede.
"""

from __future__ import annotations

import httpx

from app.modules.configuration.settings import Settings, get_settings
from app.modules.voice.domain import (
    AudioResult,
    TranscriptionResult,
    VoiceProviderError,
)

STT_TIMEOUT_SECONDS = 30.0
_STT_FILENAME = "audio"


class NvidiaTranscriptionAdapter:
    """STT via NVIDIA NIM — endpoint OpenAI-compatível `/audio/transcriptions`."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = httpx.AsyncClient(timeout=STT_TIMEOUT_SECONDS)

    async def transcribe(self, audio_bytes: bytes, *, content_type: str) -> TranscriptionResult:
        url = f"{self._settings.nvidia_base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self._settings.nvidia_api_key}"}
        files = {"file": (_STT_FILENAME, audio_bytes, content_type)}
        data = {"model": self._settings.brain_stt_model, "language": "pt"}
        try:
            response = await self._client.post(url, headers=headers, files=files, data=data)
        except httpx.HTTPError as exc:
            raise VoiceProviderError(f"STT indisponível: {exc}") from exc
        if response.status_code != 200:
            raise VoiceProviderError(
                f"STT indisponível: HTTP {response.status_code} — {response.text}"
            )
        payload = response.json()
        return TranscriptionResult(
            text=str(payload.get("text", "")).strip(),
            language="pt",
            duration_seconds=None,
        )


class EdgeTTSAdapter:
    """TTS via Microsoft Edge Neural — voz pt-BR sem chave de API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def synthesize(self, text: str) -> AudioResult:
        try:
            from edge_tts import Communicate
        except ImportError as exc:
            raise VoiceProviderError("TTS indisponível: edge-tts não instalado") from exc
        buffer = bytearray()
        try:
            communicate = Communicate(
                text, voice=self._settings.tts_voice, rate=self._settings.tts_rate
            )
            async for chunk in communicate.stream():
                data = chunk.get("data")
                if data:
                    buffer.extend(data)
        except Exception as exc:
            raise VoiceProviderError(f"TTS indisponível: {exc}") from exc
        if not buffer:
            raise VoiceProviderError("TTS indisponível: síntese vazia")
        return AudioResult(data=bytes(buffer), content_type="audio/mpeg")


class FakeSTTAdapter:
    """STT determinístico para testes — nunca toca a rede."""

    def __init__(
        self,
        stt_result: str = "texto",
        language: str = "pt",
        duration_seconds: float | None = 1.5,
    ) -> None:
        self._stt_result = stt_result
        self._language = language
        self._duration_seconds = duration_seconds

    async def transcribe(self, audio_bytes: bytes, *, content_type: str) -> TranscriptionResult:
        return TranscriptionResult(
            text=self._stt_result,
            language=self._language,
            duration_seconds=self._duration_seconds,
        )


class FakeTTSAdapter:
    """TTS determinístico para testes — nunca toca a rede."""

    def __init__(self, tts_bytes: bytes = b"fake-mp3") -> None:
        self._tts_bytes = tts_bytes

    async def synthesize(self, text: str) -> AudioResult:
        return AudioResult(data=self._tts_bytes, content_type="audio/mpeg")
