"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AudioLines,
  Bluetooth,
  Loader2,
  Mic,
  Play,
  Square,
  TriangleAlert,
  Volume2,
} from "lucide-react";
import { useAvatar } from "@/components/avatar/avatar-context";
import {
  BrowserAudioDeviceManager,
  type AudioDeviceManager,
} from "@/lib/audio-devices";
import type {
  AudioDevice,
  VoiceServerMessage,
  VoiceState,
  VoiceStatus,
} from "@/lib/types";

const VOICE_PROTOCOL_VERSION = 1;
const VOICE_AUDIO_FORMAT = "audio/webm";

async function detailOf(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown; error?: unknown };
    if (typeof body.detail === "string" && body.detail.length > 0) return body.detail;
    if (typeof body.error === "string" && body.error.length > 0) return body.error;
  } catch {
    // Resposta não-JSON: usa a mensagem genérica abaixo.
  }
  return `O backend respondeu com o status ${res.status}.`;
}

function interactionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `interaction-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function parseVoiceMessage(raw: string): VoiceServerMessage | null {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !("type" in parsed) ||
      !("version" in parsed) ||
      parsed.version !== VOICE_PROTOCOL_VERSION ||
      typeof parsed.type !== "string"
    ) return null;
    return parsed as VoiceServerMessage;
  } catch {
    return null;
  }
}

function uiStateForBackendState(state: string): VoiceState {
  switch (state) {
    case "CONNECTED": return "CONNECTING";
    case "LISTENING": return "LISTENING";
    case "TRANSCRIBING": return "TRANSCRIBING";
    case "THINKING":
    case "SYNTHESIZING": return "THINKING";
    case "RESPONDING": return "SPEAKING";
    case "IDLE":
    case "SESSION_READY": return "IDLE";
    case "ERROR": return "ERROR";
    default: return "ERROR";
  }
}

function deviceLabel(device: AudioDevice | undefined, fallback: string): string {
  return device?.label || fallback;
}

function SectionHeader({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: typeof Mic;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6]/30 to-[#00D4FF]/20 ring-1 ring-[#00D4FF]/30">
        <Icon className="size-4 text-[#00D4FF]" />
      </div>
      <div className="leading-tight">
        <h2 className="font-mono-data text-[10px] font-semibold tracking-[0.25em] text-[#94A3B8]">{title}</h2>
        <p className="text-sm font-semibold text-[#F8FAFC]">{subtitle}</p>
      </div>
    </div>
  );
}

function StateChip({ state }: { state: VoiceState }) {
  const active = state === "LISTENING";
  const tone = state === "ERROR" ? "text-[#EF4444]" : "text-[#00D4FF]";
  return (
    <span className={`flex items-center gap-2 font-mono-data text-[10px] tracking-widest ${tone}`}>
      <span className={`size-1.5 rounded-full ${active ? "animate-pulse bg-[#EF4444]" : state === "ERROR" ? "bg-[#EF4444]" : "bg-[#00D4FF]"}`} />
      {state}
    </span>
  );
}

export default function VoicePanel() {
  const { setState: setAvatarState } = useAvatar();
  const [status, setStatus] = useState<VoiceStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [voiceState, setVoiceState] = useState<VoiceState>("IDLE");
  const [connectionLabel, setConnectionLabel] = useState("Desconectada");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [responseText, setResponseText] = useState<string | null>(null);
  const [inputDevices, setInputDevices] = useState<AudioDevice[]>([]);
  const [outputDevices, setOutputDevices] = useState<AudioDevice[]>([]);
  const [selectedInputId, setSelectedInputId] = useState("");
  const [selectedOutputId, setSelectedOutputId] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [outputSelectionSupported, setOutputSelectionSupported] = useState(false);

  const managerRef = useRef<AudioDeviceManager | null>(null);
  const selectedInputIdRef = useRef("");
  const selectedOutputIdRef = useRef("");
  const socketRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const pendingAudioFormatRef = useRef("audio/mpeg");
  const turnInteractionRef = useRef<string | null>(null);
  const intentionalCloseRef = useRef(false);
  const disposedRef = useRef(false);

  const refreshDevices = useCallback(async () => {
    const manager = managerRef.current;
    if (!manager) return;
    try {
      const [inputs, outputs] = await Promise.all([manager.listInputDevices(), manager.listOutputDevices()]);
      setInputDevices(inputs);
      setOutputDevices(outputs);
      setOutputSelectionSupported(manager.canSelectOutput());
      if (selectedInputIdRef.current && !inputs.some((device) => device.deviceId === selectedInputIdRef.current)) {
        selectedInputIdRef.current = "";
        setSelectedInputId("");
      }
      if (selectedOutputIdRef.current && !outputs.some((device) => device.deviceId === selectedOutputIdRef.current)) {
        selectedOutputIdRef.current = "";
        setSelectedOutputId("");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível listar os dispositivos de áudio.");
    }
  }, []);

  useEffect(() => {
    const manager = new BrowserAudioDeviceManager();
    managerRef.current = manager;
    const unsubscribe = manager.subscribeToChanges(() => { void refreshDevices(); });
    void refreshDevices();
    return () => {
      unsubscribe();
      manager.dispose();
      managerRef.current = null;
    };
  }, [refreshDevices]);

  useEffect(() => {
    let cancelled = false;
    const loadStatus = async () => {
      try {
        const res = await fetch("/api/proxy/voice/status", { cache: "no-store" });
        if (!res.ok) throw new Error(await detailOf(res));
        const data = (await res.json()) as Partial<VoiceStatus>;
        if (!cancelled) {
          setStatus({
            stt_available: data.stt_available ?? false,
            tts_available: data.tts_available ?? false,
            stt_model: data.stt_model || "—",
            tts_voice: data.tts_voice || "—",
            protocol_version: data.protocol_version,
            audio_format: data.audio_format,
            limits: data.limits,
          });
        }
      } catch (cause) {
        if (!cancelled) setStatusError(cause instanceof Error ? cause.message : "Não foi possível consultar o status de voz.");
      }
    };
    void loadStatus();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const url = audioUrl;
    if (!url || !audioRef.current) return;
    const audio = audioRef.current;
    const manager = managerRef.current;
    void (async () => {
      if (manager) await manager.setOutputElement(audio);
      try {
        await audio.play();
        setVoiceState("SPEAKING");
        setAvatarState("speaking");
      } catch {
        setError("A resposta chegou, mas o navegador bloqueou a reprodução automática.");
        setVoiceState("ERROR");
        setAvatarState("error");
      }
    })();
  }, [audioUrl, setAvatarState]);

  const releaseAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute("src");
      audioRef.current.load();
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setAudioUrl(null);
  }, []);

  const releaseInput = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
    turnInteractionRef.current = null;
  }, []);

  const stopSession = useCallback(() => {
    intentionalCloseRef.current = true;
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    releaseInput();
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "voice.session.stop", version: VOICE_PROTOCOL_VERSION }));
      socket.close(1000, "client stopped");
    }
    socketRef.current = null;
    setSessionReady(false);
    setSessionId(null);
    setConnectionLabel("Desconectada");
    setVoiceState("IDLE");
    setAvatarState("idle");
    releaseAudio();
  }, [releaseAudio, releaseInput, setAvatarState]);

  const startSession = useCallback(async () => {
    if (socketRef.current && socketRef.current.readyState !== WebSocket.CLOSED) return;
    setError(null);
    setVoiceState("CONNECTING");
    setConnectionLabel("Solicitando acesso ao microfone…");
    intentionalCloseRef.current = false;
    try {
      const manager = managerRef.current;
      if (!manager) throw new Error("Gerenciador de áudio indisponível.");
      await manager.requestInputPermission();
      await refreshDevices();

      const sessionResponse = await fetch("/api/proxy/conversation/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!sessionResponse.ok) throw new Error(await detailOf(sessionResponse));
      const sessionPayload = (await sessionResponse.json()) as { session_id?: unknown };
      if (typeof sessionPayload.session_id !== "string" || !sessionPayload.session_id) throw new Error("O backend não retornou uma sessão de conversa válida.");

      const wsInfoResponse = await fetch(`/api/ws-info?purpose=voice&session_id=${encodeURIComponent(sessionPayload.session_id)}`, { cache: "no-store" });
      if (!wsInfoResponse.ok) throw new Error(await detailOf(wsInfoResponse));
      const wsInfo = (await wsInfoResponse.json()) as { ticket?: unknown; ws_base?: unknown };
      if (typeof wsInfo.ticket !== "string" || typeof wsInfo.ws_base !== "string") throw new Error("O backend não retornou um ticket de voz válido.");

      const wsUrl = new URL(wsInfo.ws_base);
      wsUrl.searchParams.set("ticket", wsInfo.ticket);
      const socket = new WebSocket(wsUrl.toString());
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;
      setSessionId(sessionPayload.session_id);
      setConnectionLabel("Conectando sessão segura…");

      socket.onopen = () => {
        setConnectionLabel("Conectada");
        socket.send(JSON.stringify({
          type: "voice.session.start",
          version: VOICE_PROTOCOL_VERSION,
          session_id: sessionPayload.session_id,
          interaction_id: interactionId(),
        }));
      };

      socket.onmessage = (event) => {
        if (typeof event.data !== "string") {
          const blob = event.data instanceof Blob ? event.data : new Blob([event.data], { type: pendingAudioFormatRef.current });
          if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
          const nextUrl = URL.createObjectURL(blob);
          audioUrlRef.current = nextUrl;
          setAudioUrl(nextUrl);
          setVoiceState("SPEAKING");
          setAvatarState("speaking");
          return;
        }

        const message = parseVoiceMessage(event.data);
        if (!message) {
          setError("O servidor enviou uma mensagem de voz inválida.");
          setVoiceState("ERROR");
          return;
        }
        switch (message.type) {
          case "voice.session.started":
            setSessionReady(true);
            setConnectionLabel("Conectada");
            setVoiceState("IDLE");
            break;
          case "voice.state": {
            const nextState = uiStateForBackendState(message.state);
            if (nextState === "IDLE" && audioRef.current && !audioRef.current.paused && !audioRef.current.ended) break;
            setVoiceState(nextState);
            if (nextState === "LISTENING") setAvatarState("listening");
            if (nextState === "THINKING") setAvatarState("thinking");
            if (nextState === "ERROR") setAvatarState("error");
            break;
          }
          case "voice.transcript.final":
            setTranscript(message.text);
            setVoiceState("THINKING");
            setAvatarState("thinking");
            break;
          case "voice.response.started":
            setVoiceState("THINKING");
            setAvatarState("thinking");
            break;
          case "voice.response.text":
            setResponseText(message.text);
            break;
          case "voice.response.audio":
            pendingAudioFormatRef.current = message.format;
            break;
          case "voice.response.completed":
            if (!audioRef.current || audioRef.current.paused || audioRef.current.ended) {
              setVoiceState("IDLE");
              setAvatarState("idle");
            }
            break;
          case "voice.session.stopped":
            setSessionReady(false);
            setConnectionLabel("Desconectada");
            break;
          case "voice.error":
            setError(message.message);
            setVoiceState("ERROR");
            setAvatarState("error");
            break;
        }
      };

      socket.onerror = () => {
        setError("A conexão de voz falhou.");
        setVoiceState("ERROR");
        setAvatarState("error");
      };
      socket.onclose = () => {
        releaseInput();
        socketRef.current = null;
        setSessionReady(false);
        setConnectionLabel("Desconectada");
        if (!intentionalCloseRef.current && !disposedRef.current) {
          setError("A sessão de voz foi desconectada.");
          setVoiceState("ERROR");
          setAvatarState("error");
        } else {
          setVoiceState("IDLE");
          setAvatarState("idle");
        }
      };
    } catch (cause) {
      releaseInput();
      setVoiceState("ERROR");
      setAvatarState("error");
      if (cause instanceof DOMException && cause.name === "NotAllowedError") setError("Permissão de microfone negada. Habilite o acesso e tente novamente.");
      else if (cause instanceof DOMException && cause.name === "NotFoundError") setError("Nenhum microfone encontrado neste dispositivo.");
      else setError(cause instanceof Error ? cause.message : "Não foi possível iniciar a sessão de voz.");
    }
  }, [refreshDevices, releaseInput, setAvatarState]);

  const startTurn = useCallback(async () => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN || !sessionReady) {
      setError("Inicie uma sessão de voz antes de falar.");
      return;
    }
    if (typeof MediaRecorder === "undefined") {
      setError("Seu navegador não suporta captura de áudio (MediaRecorder).");
      return;
    }
    setError(null);
    releaseInput();
    try {
      const constraints: MediaStreamConstraints = selectedInputId ? { audio: { deviceId: { exact: selectedInputId } } } : { audio: true };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      if (!mimeType) throw new Error("O navegador não oferece o formato audio/webm suportado pela V0.");
      const recorder = new MediaRecorder(stream, { mimeType });
      const currentInteractionId = interactionId();
      turnInteractionRef.current = currentInteractionId;
      recorderRef.current = recorder;
      recorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) socket.send(event.data);
      });
      recorder.addEventListener("stop", () => {
        if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "voice.turn.end", version: VOICE_PROTOCOL_VERSION }));
        releaseInput();
      });
      socket.send(JSON.stringify({
        type: "voice.turn.start",
        version: VOICE_PROTOCOL_VERSION,
        format: VOICE_AUDIO_FORMAT,
        interaction_id: currentInteractionId,
      }));
      recorder.start(250);
      setVoiceState("LISTENING");
      setAvatarState("listening");
    } catch (cause) {
      releaseInput();
      if (cause instanceof DOMException && cause.name === "NotAllowedError") setError("Permissão de microfone negada. Habilite o acesso e tente novamente.");
      else if (cause instanceof DOMException && cause.name === "NotFoundError") setError("O microfone selecionado não está disponível.");
      else setError(cause instanceof Error ? cause.message : "Não foi possível iniciar o turno de voz.");
      setVoiceState("ERROR");
      setAvatarState("error");
    }
  }, [releaseInput, selectedInputId, sessionReady, setAvatarState]);

  const stopTurn = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
  }, []);

  const selectInput = useCallback(async (id: string) => {
    selectedInputIdRef.current = id;
    setSelectedInputId(id);
    await managerRef.current?.selectInput(id);
  }, []);

  const selectOutput = useCallback(async (id: string) => {
    selectedOutputIdRef.current = id;
    setSelectedOutputId(id);
    const manager = managerRef.current;
    if (!manager) return;
    await manager.selectOutput(id);
    setOutputSelectionSupported(manager.canSelectOutput());
  }, []);

  useEffect(() => {
    return () => {
      disposedRef.current = true;
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        try { recorder.stop(); } catch { /* recorder já foi encerrado pelo navegador */ }
      }
      releaseInput();
      const socket = socketRef.current;
      if (socket && socket.readyState === WebSocket.OPEN) socket.close(1000, "page closed");
      releaseAudio();
    };
  }, [releaseAudio, releaseInput]);

  const inputLabel = deviceLabel(inputDevices.find((device) => device.deviceId === selectedInputId), "Padrão do sistema");
  const outputLabel = deviceLabel(outputDevices.find((device) => device.deviceId === selectedOutputId), "Padrão do sistema");
  const busy = voiceState === "CONNECTING" || voiceState === "TRANSCRIBING" || voiceState === "THINKING";
  const recording = voiceState === "LISTENING";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="glass flex items-center gap-2 rounded-full px-3 py-1.5 font-mono-data text-[10px] tracking-wider text-[#94A3B8]"><span className={sessionReady ? "dot-ok" : "dot-danger"} />VOICE V1 <span className="text-[#64748B]">· {connectionLabel}</span></span>
        <StateChip state={voiceState} />
        {status ? <span className="font-mono-data text-[10px] tracking-wider text-[#64748B]">STT {status.stt_available ? "OK" : "INDISPONÍVEL"} · TTS {status.tts_available ? "OK" : "INDISPONÍVEL"}</span> : <Loader2 className="size-3.5 animate-spin text-[#00D4FF]" />}
      </div>

      {statusError || error ? <p className="flex items-center gap-2 rounded-xl border border-[#EF4444]/30 bg-[#EF4444]/10 p-3 text-sm text-[#FCA5A5]"><TriangleAlert className="size-4 shrink-0" />{error || statusError}</p> : null}

      <section className="glass glass-hover animate-fade-up rounded-2xl p-5">
        <SectionHeader icon={Bluetooth} title="SOPHIE VOICE V0" subtitle="O sistema operacional gerencia o pareamento Bluetooth" />
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2 text-sm text-[#CBD5E1]">
            <span className="flex items-center gap-2 font-mono-data text-[10px] tracking-widest text-[#94A3B8]"><Mic className="size-3.5 text-[#00D4FF]" /> ENTRADA / MICROFONE</span>
            <select value={selectedInputId} onChange={(event) => void selectInput(event.target.value)} className="w-full rounded-xl border border-white/[0.08] bg-black/20 p-3 text-sm text-[#F8FAFC] outline-none focus:border-[#00D4FF]/50"><option value="">Padrão do sistema</option>{inputDevices.map((device) => <option key={device.deviceId} value={device.deviceId}>{device.label}</option>)}</select>
            <span className="block text-xs text-[#64748B]">Atual: {inputLabel}</span>
          </label>
          <label className="space-y-2 text-sm text-[#CBD5E1]">
            <span className="flex items-center gap-2 font-mono-data text-[10px] tracking-widest text-[#94A3B8]"><Volume2 className="size-3.5 text-[#00D4FF]" /> SAÍDA / FONE</span>
            <select value={selectedOutputId} onChange={(event) => void selectOutput(event.target.value)} className="w-full rounded-xl border border-white/[0.08] bg-black/20 p-3 text-sm text-[#F8FAFC] outline-none focus:border-[#00D4FF]/50"><option value="">Padrão do sistema</option>{outputDevices.map((device) => <option key={device.deviceId} value={device.deviceId}>{device.label}</option>)}</select>
            <span className="block text-xs text-[#64748B]">Atual: {outputLabel} · {outputSelectionSupported ? "seleção suportada" : "saída segue o padrão do navegador"}</span>
          </label>
        </div>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => (sessionReady ? stopSession() : void startSession())} disabled={voiceState === "CONNECTING"} className="inline-flex items-center gap-2 rounded-xl border border-[#00D4FF]/40 bg-[#00D4FF]/10 px-4 py-2.5 text-sm font-medium text-[#00D4FF] transition-colors hover:bg-[#00D4FF]/20 disabled:cursor-not-allowed disabled:opacity-40">{voiceState === "CONNECTING" ? <Loader2 className="size-4 animate-spin" /> : sessionReady ? <Square className="size-4" /> : <Play className="size-4" />}{voiceState === "CONNECTING" ? "Conectando…" : sessionReady ? "Encerrar sessão" : "Iniciar sessão de voz"}</button>
          <span className="text-xs text-[#64748B]">O microfone só é solicitado depois deste clique.</span>
        </div>
      </section>

      <section className="glass glass-hover animate-fade-up rounded-2xl p-5">
        <SectionHeader icon={AudioLines} title="TURNO DE VOZ" subtitle="Push-to-talk: fale, pare e aguarde a resposta" />
        <div className="flex flex-col items-center gap-4 py-2">
          <button type="button" onClick={() => (recording ? stopTurn() : void startTurn())} disabled={!sessionReady || busy} aria-label={recording ? "Parar turno de voz" : "Começar turno de voz"} className="relative flex size-20 items-center justify-center rounded-full border border-[#00D4FF]/35 bg-[#00D4FF]/10 text-[#00D4FF] shadow-[0_0_24px_-6px_rgba(0,212,255,0.55)] transition-all disabled:cursor-not-allowed disabled:opacity-40">{recording && <span className="absolute inset-0 animate-ping-soft rounded-full bg-[#EF4444]/40" />}<span className="relative">{recording ? <Square className="size-6 fill-current text-[#EF4444]" /> : <Mic className="size-7" />}</span></button>
          <StateChip state={voiceState} />
          {!sessionReady ? <p className="text-center text-xs text-[#64748B]">Inicie a sessão para habilitar o microfone.</p> : recording ? <p className="text-center text-xs text-[#EF4444]">LISTENING · o áudio não é salvo em disco.</p> : <p className="text-center text-xs text-[#64748B]">Clique no microfone, fale e clique novamente para enviar.</p>}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="glass rounded-2xl p-5"><p className="font-mono-data text-[10px] tracking-[0.25em] text-[#00D4FF]">TRANSCRIÇÃO</p><p className="mt-3 min-h-16 text-sm leading-relaxed text-[#E2E8F0]">{transcript || "A fala reconhecida aparecerá aqui."}</p></div>
        <div className="glass rounded-2xl p-5"><p className="font-mono-data text-[10px] tracking-[0.25em] text-[#00D4FF]">SOPHIE</p><p className="mt-3 min-h-16 text-sm leading-relaxed text-[#E2E8F0]">{responseText || "A resposta da Sophie aparecerá aqui."}</p><audio ref={audioRef} controls src={audioUrl || undefined} className="mt-4 w-full" onEnded={() => { if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current); audioUrlRef.current = null; setAudioUrl(null); setVoiceState("IDLE"); setAvatarState("idle"); }} onError={() => { setError("Não foi possível reproduzir o áudio da Sophie."); setVoiceState("ERROR"); setAvatarState("error"); }} /></div>
      </section>

      <p className="text-xs leading-relaxed text-[#64748B]">Bluetooth é tratado pelo sistema operacional como entrada e saída de áudio. A V0 usa WebSocket autenticado por ticket de curta duração, mantém o contexto da sessão e descarta o áudio bruto após o STT. <Link href="/conversa" className="text-[#93C5FD] hover:text-[#DBEAFE]">Abrir conversa textual</Link></p>
      {sessionId ? <p className="font-mono-data text-[10px] text-[#475569]">session_id: {sessionId}</p> : null}
    </div>
  );
}
