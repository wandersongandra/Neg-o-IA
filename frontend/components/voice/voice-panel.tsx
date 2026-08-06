"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AudioLines,
  Bot,
  Loader2,
  MessageSquareText,
  Mic,
  Play,
  Square,
  TriangleAlert,
  Volume2,
} from "lucide-react";
import { useAvatar } from "@/components/avatar/avatar-context";

interface VoiceStatus {
  stt_available: boolean;
  tts_available: boolean;
  stt_model: string;
  tts_voice: string;
}

async function detailOf(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    // corpo não é JSON — usa mensagem genérica
  }
  return `O backend respondeu com o status ${res.status}.`;
}

function formatElapsed(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function StatusChip({
  label,
  ok,
  value,
}: {
  label: string;
  ok: boolean;
  value: string;
}) {
  return (
    <span
      className="glass flex items-center gap-2 rounded-full px-3 py-1.5 font-mono-data text-[10px] tracking-wider text-[#94A3B8]"
      title={`${label}: ${ok ? "disponível" : "indisponível"} (${value})`}
    >
      <span className={ok ? "dot-ok" : "dot-danger"} />
      {label}
      <span className={ok ? "text-[#22C55E]" : "text-[#EF4444]"}>
        {ok ? "DISPONÍVEL" : "INDISPONÍVEL"}
      </span>
      <span className="hidden text-[#64748B] sm:inline">· {value}</span>
    </span>
  );
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
        <h2 className="font-mono-data text-[10px] font-semibold tracking-[0.25em] text-[#94A3B8]">
          {title}
        </h2>
        <p className="text-sm font-semibold text-[#F8FAFC]">{subtitle}</p>
      </div>
    </div>
  );
}

export default function VoicePanel() {
  const { setState: setAvatarState, speak } = useAvatar();
  const router = useRouter();
  const [status, setStatus] = useState<VoiceStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [transcription, setTranscription] = useState<string | null>(null);
  const [transcribeError, setTranscribeError] = useState<string | null>(null);

  const [ttsText, setTtsText] = useState("");
  const [synthesizing, setSynthesizing] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [ttsError, setTtsError] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioUrlRef = useRef<string | null>(null);
  const disposedRef = useRef(false);
  const pendingAutoText = useRef<string | null>(null);
  const autoSendRef = useRef(false);
  const [autoSend, setAutoSend] = useState(false);

  useEffect(() => {
    autoSendRef.current = autoSend;
  }, [autoSend]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch("/api/proxy/voice/status", {
          cache: "no-store",
        });
        if (!res.ok) {
          if (!cancelled) setStatusError(await detailOf(res));
          return;
        }
        const data = (await res.json()) as Partial<VoiceStatus>;
        if (!cancelled) {
          setStatus({
            stt_available: data.stt_available ?? false,
            tts_available: data.tts_available ?? false,
            stt_model: data.stt_model || "—",
            tts_voice: data.tts_voice || "—",
          });
        }
      } catch {
        if (!cancelled) {
          setStatusError("Não foi possível consultar o status de voz do backend.");
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const text = new URLSearchParams(window.location.search).get("text");
    if (text) {
      pendingAutoText.current = text;
      setTtsText(text);
    }
  }, []);

  const transcribe = useCallback(async (blob: Blob) => {
    setTranscribing(true);
    setTranscribeError(null);
    try {
      const form = new FormData();
      form.append("file", blob, "gravacao.webm");
      const res = await fetch("/api/proxy/voice/transcribe", {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(await detailOf(res));
      const data = (await res.json()) as { text?: unknown };
      if (typeof data.text !== "string") {
        throw new Error("O backend retornou uma resposta inválida.");
      }
      setTranscription(data.text);
      if (autoSendRef.current && data.text.trim()) {
        router.push(`/conversa?text=${encodeURIComponent(data.text.trim())}`);
        return;
      }
    } catch (err) {
      setTranscribeError(
        err instanceof Error ? err.message : "Falha ao transcrever o áudio.",
      );
    } finally {
      setTranscribing(false);
    }
  }, []);

  const synthesize = useCallback(async (text: string) => {
    setSynthesizing(true);
    setTtsError(null);
    try {
      const res = await fetch("/api/proxy/voice/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error(await detailOf(res));
      const buffer = await res.arrayBuffer();
       const url = URL.createObjectURL(
        new Blob([buffer], { type: "audio/mpeg" }),
      );
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = url;
      setAudioUrl(url);
      const audio = new Audio(url);
      audio.onended = () => {
        setAvatarState("idle");
      };
      audio.onerror = () => {
        setAvatarState("idle");
      };
      setAvatarState("speaking");
      speak(audio);
    } catch (err) {
      setTtsError(
        err instanceof Error ? err.message : "Falha ao sintetizar a fala.",
      );
    } finally {
      setSynthesizing(false);
    }
  }, [setAvatarState, speak]);

  useEffect(() => {
    if (!pendingAutoText.current) return;
    if (!status) return;
    const text = pendingAutoText.current;
    pendingAutoText.current = null;
    if (status.tts_available) {
      void synthesize(text);
    } else {
      setTtsError(
        "TTS indisponível no momento — o texto foi preenchido para tentar manualmente.",
      );
    }
  }, [status, synthesize]);

  const startRecording = useCallback(async () => {
    setMediaError(null);
    if (typeof MediaRecorder === "undefined") {
      setMediaError(
        "Seu navegador não suporta gravação de áudio (MediaRecorder).",
      );
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "";
      const recorder = new MediaRecorder(
        stream,
        mimeType ? { mimeType } : undefined,
      );
      recorderRef.current = recorder;
      chunksRef.current = [];
      recorder.addEventListener("dataavailable", (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      });
      recorder.addEventListener("stop", () => {
        if (disposedRef.current) return;
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        void transcribe(blob);
      });
      recorder.start();
      setRecording(true);
      setElapsed(0);
      setAvatarState("listening");
    } catch (err) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      if (err instanceof DOMException && err.name === "NotAllowedError") {
        setMediaError(
          "Permissão de microfone negada. Habilite o acesso e tente novamente.",
        );
      } else if (err instanceof DOMException && err.name === "NotFoundError") {
        setMediaError("Nenhum microfone encontrado neste dispositivo.");
      } else {
        setMediaError("Não foi possível acessar o microfone.");
      }
    }
  }, [transcribe, setAvatarState]);

  const handleStop = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
    setRecording(false);
    setElapsed(0);
    setAvatarState("idle");
  }, [setAvatarState]);

  useEffect(() => {
    if (!recording) return;
    const id = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [recording]);

  useEffect(() => {
    return () => {
      disposedRef.current = true;
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        try {
          recorder.stop();
        } catch {
          // já inativo
        }
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = null;
      }
    };
  }, []);

  const sttDisabled = !status?.stt_available || transcribing;
  const ttsDisabled = !status?.tts_available || synthesizing || !ttsText.trim();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2.5">
        {status ? (
          <>
            <StatusChip
              label="STT"
              ok={status.stt_available}
              value={status.stt_model}
            />
            <StatusChip
              label="TTS"
              ok={status.tts_available}
              value={status.tts_voice}
            />
          </>
        ) : (
          <span className="flex items-center gap-2 font-mono-data text-[10px] tracking-wider text-[#64748B]">
            <Loader2 className="size-3.5 animate-spin text-[#00D4FF]" />
            VERIFICANDO VOZ…
          </span>
        )}
        {statusError ? (
          <span className="flex items-center gap-2 rounded-full border border-[#EF4444]/30 bg-[#EF4444]/10 px-3 py-1.5 font-mono-data text-[10px] tracking-wider text-[#EF4444]">
            <TriangleAlert className="size-3.5" />
            {statusError}
          </span>
        ) : null}
      </div>

      <section className="glass glass-hover animate-fade-up rounded-2xl p-5">
        <SectionHeader
          icon={AudioLines}
          title="FALAR COM O NEGÃO (STT)"
          subtitle="Grave sua pergunta e veja a transcrição"
        />

        <div className="flex flex-col items-center gap-4 py-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              role="switch"
              aria-checked={autoSend}
              onClick={() => setAutoSend((v) => !v)}
              className={`relative h-6 w-11 rounded-full transition-colors ${
                autoSend
                  ? "bg-[#00D4FF]/70 shadow-[0_0_16px_-4px_rgba(0,212,255,0.8)]"
                  : "bg-white/10"
              }`}
              title="Ao parar de gravar, transcrição vai direto para o chat com o NEGÃO"
            >
              <span
                className={`absolute top-0.5 size-5 rounded-full bg-white transition-all ${
                  autoSend ? "left-[22px]" : "left-0.5"
                }`}
              />
            </button>
            <span className="flex items-center gap-1.5 text-xs text-[#94A3B8]">
              <Bot className="size-3.5 text-[#00D4FF]" />
              Enviar direto para o chat
            </span>
          </div>

          <button
            type="button"
            onClick={recording ? handleStop : () => void startRecording()}
            disabled={sttDisabled}
            aria-label={recording ? "Parar gravação" : "Começar a gravar"}
            title={
              sttDisabled
                ? transcribing
                  ? "Transcrevendo o áudio…"
                  : "STT indisponível no backend"
                : undefined
            }
            className="relative flex size-20 items-center justify-center rounded-full transition-all duration-300 disabled:cursor-not-allowed disabled:opacity-40"
            style={
              recording
                ? {
                    border: "1px solid rgba(239, 68, 68, 0.6)",
                    background: "rgba(239, 68, 68, 0.15)",
                    color: "#ef4444",
                    boxShadow: "0 0 30px -6px rgba(239, 68, 68, 0.7)",
                  }
                : {
                    border: "1px solid rgba(0, 212, 255, 0.35)",
                    background: "rgba(0, 212, 255, 0.1)",
                    color: "#00d4ff",
                    boxShadow: "0 0 24px -6px rgba(0, 212, 255, 0.55)",
                  }
            }
          >
            {recording && (
              <span className="absolute inset-0 animate-ping-soft rounded-full bg-[#EF4444]/40" />
            )}
            <span className="relative">
              {transcribing ? (
                <Loader2 className="size-7 animate-spin" />
              ) : recording ? (
                <Square className="size-6 fill-current" />
              ) : (
                <Mic className="size-7" />
              )}
            </span>
          </button>

          {recording && (
            <p className="flex items-center gap-2 font-mono-data text-[11px] tracking-widest text-[#EF4444]">
              <span className="size-1.5 animate-pulse rounded-full bg-[#EF4444] shadow-[0_0_8px_currentColor]" />
              GRAVANDO {formatElapsed(elapsed)}
            </p>
          )}
          {!recording && !transcribing && (
            <p className="text-center text-xs text-[#64748B]">
              Clique no microfone para começar a gravar.
              {autoSend
                ? " Ao parar, a transcrição vai direto para o chat."
                : " A transcrição é enviada ao NEGÃO assim que você parar."}
            </p>
          )}

          {sttDisabled && !transcribing && !recording ? (
            <p className="flex items-center gap-2 text-xs text-[#F59E0B]">
              <TriangleAlert className="size-3.5" />
              Transcrição de voz (STT) indisponível no backend.
            </p>
          ) : null}

          {mediaError ? (
            <p className="flex items-center gap-2 text-xs text-[#EF4444]">
              <TriangleAlert className="size-3.5 shrink-0" />
              {mediaError}
            </p>
          ) : null}

          {transcribing ? (
            <p className="flex items-center gap-2 text-xs text-[#00D4FF]">
              <Loader2 className="size-3.5 animate-spin" />
              Transcrevendo…
            </p>
          ) : null}

          {transcribeError ? (
            <p className="flex items-center gap-2 text-xs text-[#EF4444]">
              <TriangleAlert className="size-3.5 shrink-0" />
              {transcribeError}
            </p>
          ) : null}

          {transcription ? (
            <div className="w-full rounded-xl border border-[#00D4FF]/20 bg-[#00D4FF]/5 p-4">
              <p className="font-mono-data text-[10px] tracking-[0.25em] text-[#00D4FF]">
                TRANSCRIÇÃO
              </p>
              <p className="mt-2 text-sm leading-relaxed text-[#E2E8F0]">
                {transcription}
              </p>
              <Link
                href={`/conversa?text=${encodeURIComponent(transcription)}`}
                className="mt-3 inline-flex items-center gap-2 rounded-lg border border-[#3B82F6]/40 bg-[#3B82F6]/10 px-3 py-1.5 text-xs font-medium text-[#93C5FD] transition-colors hover:bg-[#3B82F6]/20 hover:text-[#DBEAFE]"
              >
                <MessageSquareText className="size-3.5" />
                Usar texto transcrito no chat
              </Link>
            </div>
          ) : null}
        </div>
      </section>

      <section className="glass glass-hover animate-fade-up rounded-2xl p-5">
        <SectionHeader
          icon={Volume2}
          title="OUVIR O NEGÃO (TTS)"
          subtitle="Escreva algo e escute a voz do NEGÃO"
        />

        <div className="space-y-3">
          <textarea
            value={ttsText}
            onChange={(e) => setTtsText(e.target.value)}
            rows={4}
            placeholder="O que o NEGÃO deve falar?"
            disabled={!status?.tts_available}
            className="w-full resize-none rounded-xl border border-white/[0.06] bg-black/20 p-3 text-sm text-[#F8FAFC] outline-none transition-colors placeholder:text-[#64748B] focus:border-[#00D4FF]/40 disabled:cursor-not-allowed disabled:opacity-50"
          />
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => void synthesize(ttsText.trim())}
              disabled={ttsDisabled}
              className="inline-flex items-center gap-2 rounded-xl border border-[#00D4FF]/40 bg-[#00D4FF]/10 px-4 py-2 text-sm font-medium text-[#00D4FF] transition-all hover:bg-[#00D4FF]/20 hover:shadow-[0_0_24px_-8px_rgba(0,212,255,0.7)] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {synthesizing ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Play className="size-4" />
              )}
              {synthesizing ? "Sintetizando…" : "Falar"}
            </button>
            {!status?.tts_available ? (
              <span className="flex items-center gap-2 text-xs text-[#F59E0B]">
                <TriangleAlert className="size-3.5" />
                Síntese de voz (TTS) indisponível no backend.
              </span>
            ) : null}
          </div>

          {ttsError ? (
            <p className="flex items-center gap-2 text-xs text-[#EF4444]">
              <TriangleAlert className="size-3.5 shrink-0" />
              {ttsError}
            </p>
          ) : null}

          {audioUrl ? (
            <audio
              key={audioUrl}
              controls
              autoPlay
              src={audioUrl}
              className="w-full"
            />
          ) : null}
        </div>
      </section>
    </div>
  );
}
