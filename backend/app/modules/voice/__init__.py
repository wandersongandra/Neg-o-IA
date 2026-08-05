"""Módulo voice — entrada de fala (ASR) e saída de voz (TTS).

v0: esqueleto de contrato. Implementação efetiva em v4+ (Sentidos).
"""

from __future__ import annotations

from app.modules.voice.domain import VoicePort

__all__ = ["VoicePort"]
