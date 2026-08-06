"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Check,
  Copy,
  Loader2,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  Send,
  Square,
  Wifi,
  WifiOff,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  History,
  Trash2,
  Edit3,
  X,
} from "lucide-react";
import Markdown from "@/components/chat/markdown";
import PromptSuggestions from "@/components/chat/prompt-suggestions";
import TypingIndicator from "@/components/chat/typing-indicator";
import type { LucideIcon } from "lucide-react";
import type {
  ChatViewMessage,
  ConversationMessageResponse,
  ConversationSession,
  WsInfo,
  WsServerMessage,
} from "@/lib/types";
import { useAvatar } from "@/components/avatar/avatar-context";
import { useToast } from "@/components/ui/toast";

type WsStatus = "conectando" | "online" | "offline";

const RECONNECT_DELAYS_MS = [1000, 3000, 5000];
const HEARTBEAT_INTERVAL_MS = 45_000;

const STATUS_META: Record<
  WsStatus,
  { label: string; color: string; icon: LucideIcon; spinning?: boolean }
> = {
  conectando: { label: "conectando", color: "#F59E0B", icon: Loader2, spinning: true },
  online: { label: "online", color: "#22C55E", icon: Wifi },
  offline: { label: "offline", color: "#EF4444", icon: WifiOff },
};

export default function ChatPanel() {
  const { setState: setAvatarState, speak, stopSpeaking } = useAvatar();
  const { toast } = useToast();
  const [status, setStatus] = useState<WsStatus>("conectando");
  const [messages, setMessages] = useState<ChatViewMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [wsBase, setWsBase] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [ttsMuted, setTtsMuted] = useState(false);
  const [sessions, setSessions] = useState<ConversationSession[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [regenMessageId, setRegenMessageId] = useState<string | null>(null);
  const [thinking, setThinking] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const hasUserMessageRef = useRef(false);
  const sendingRef = useRef(false);
  const ttsMutedRef = useRef(ttsMuted);
  const pendingAssistantRef = useRef<string | null>(null);
  const genTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recordingSecondsRef = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    ttsMutedRef.current = ttsMuted;
  }, [ttsMuted]);

  const clearGenTimer = useCallback(() => {
    if (genTimerRef.current) {
      clearTimeout(genTimerRef.current);
      genTimerRef.current = null;
    }
  }, []);

  const autoResizeTextarea = useCallback((el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
  }, []);

  // Fetch ws-info on mount
  useEffect(() => {
    let cancelled = false;
    fetch("/api/ws-info", { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error(`ws-info ${res.status}`);
        return res.json() as Promise<WsInfo>;
      })
      .then((info) => {
        if (cancelled) return;
        setApiKey(info.api_key);
        setWsBase(info.ws_base);
      })
      .catch(() => {
        if (!cancelled) setStatus("offline");
      });
    return () => { cancelled = true; };
  }, []);

  // Fetch sessions list
  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch("/api/proxy/conversation/sessions");
      if (!res.ok) return;
      const data = await res.json() as { sessions: ConversationSession[] };
      setSessions(data.sessions ?? []);
    } catch {
      setSessions([]);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Auto-send from ?text= (ex.: página de voz)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const text = params.get("text");
    const sid = params.get("session");
    if (sid) {
      window.history.replaceState({}, "", window.location.pathname);
      void loadSession(sid);
    } else if (text) {
      const clean = text.trim();
      if (!clean) return;
      window.history.replaceState({}, "", window.location.pathname);
      const t = setTimeout(() => void sendMessage(clean), 400);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // WebSocket connection
  useEffect(() => {
    if (!apiKey) return;

    let disposed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;

    const clearReconnect = () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    const handleServerMessage = (raw: string) => {
      let msg: WsServerMessage;
      try {
        msg = JSON.parse(raw) as WsServerMessage;
      } catch {
        return;
      }

      switch (msg.type) {
        case "session":
          if (!sessionIdRef.current) {
            sessionIdRef.current = msg.session_id;
          }
          setSessionId(sessionIdRef.current);
          break;
        case "tokens":
          hasUserMessageRef.current = true;
          setThinking(false);
          setAvatarState("thinking");
          setMessages((prev) => {
            const copy = [...prev];
            for (let i = copy.length - 1; i >= 0; i--) {
              const m = copy[i];
              if (m.role === "assistant" && m.status === "streaming") {
                copy[i] = { ...m, content: m.content + msg.delta };
                break;
              }
            }
            return copy;
          });
          break;
        case "done":
          clearGenTimer();
          sessionIdRef.current = msg.session_id;
          setSessionId(msg.session_id);
          setMessages((prev) => {
            const copy = [...prev];
            for (let i = copy.length - 1; i >= 0; i--) {
              const m = copy[i];
              if (m.role === "assistant" && m.status === "streaming") {
                copy[i] = {
                  ...m,
                  status: "done",
                  content: msg.text,
                  model: msg.model,
                  latency_ms: msg.latency_ms,
                  fallback_used: msg.fallback_used,
                };
                break;
              }
            }
            return copy;
          });
          sendingRef.current = false;
          pendingAssistantRef.current = null;
          setSending(false);
          setThinking(false);
          if (!ttsMutedRef.current && msg.text.trim()) {
            setAvatarState("speaking");
            synthesizeAndSpeak(msg.text);
          } else {
            setAvatarState("idle");
          }
          break;
        case "error":
          clearGenTimer();
          setAvatarState("error");
          setMessages((prev) => {
            const copy = [...prev];
            for (let i = copy.length - 1; i >= 0; i--) {
              const m = copy[i];
              if (m.role === "assistant" && m.status === "streaming") {
                copy[i] = { ...m, status: "error", content: msg.detail };
                break;
              }
            }
            return copy;
          });
          sendingRef.current = false;
          pendingAssistantRef.current = null;
          setSending(false);
          setThinking(false);
          setTimeout(() => setAvatarState("idle"), 3000);
          break;
        case "pong":
          break;
      }
    };

    const scheduleReconnect = () => {
      if (disposed) return;
      setStatus("conectando");
      const delay = RECONNECT_DELAYS_MS[Math.min(attempt, RECONNECT_DELAYS_MS.length - 1)];
      attempt += 1;
      clearReconnect();
      reconnectTimer = setTimeout(connect, delay);
    };

    function connect() {
      if (disposed) return;
      setStatus("conectando");

      let url: string;
      if (wsBase !== null) {
        url = `${wsBase}/ws/conversation?api_key=${apiKey}`;
      } else {
        const protocol = location.protocol === "https:" ? "wss" : "ws";
        url = `${protocol}://${location.host}/ws/conversation?api_key=${apiKey}`;
      }

      let nextSocket: WebSocket;
      try {
        nextSocket = new WebSocket(url);
      } catch {
        scheduleReconnect();
        return;
      }

      socket = nextSocket;
      wsRef.current = nextSocket;

      nextSocket.onopen = () => {
        if (disposed) return;
        setStatus("online");
        attempt = 0;
        nextSocket.send(JSON.stringify({ type: "start" }));
      };

      nextSocket.onmessage = (ev: MessageEvent<string>) => {
        if (!disposed) handleServerMessage(ev.data);
      };

      nextSocket.onerror = () => {
        nextSocket.close();
      };

      nextSocket.onclose = () => {
        if (wsRef.current === nextSocket) wsRef.current = null;
        if (disposed) return;
        scheduleReconnect();
      };
    }

    connect();

    return () => {
      disposed = true;
      clearReconnect();
      if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;
        socket.close();
      }
      wsRef.current = null;
    };

    function synthesizeAndSpeak(text: string) {
      fetch("/api/proxy/voice/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      })
        .then((res) => {
          if (!res.ok) throw new Error("TTS falhou");
          return res.blob();
        })
        .then((blob) => {
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.onended = () => {
            URL.revokeObjectURL(url);
            setAvatarState("idle");
          };
          audio.onerror = () => {
            URL.revokeObjectURL(url);
            setAvatarState("idle");
          };
          speak(audio);
          void audio.play().catch(() => {
            URL.revokeObjectURL(url);
            setAvatarState("idle");
          });
        })
        .catch((e) => {
          console.warn("TTS failed:", e);
          setAvatarState("idle");
        });
    }
  }, [apiKey, wsBase, setAvatarState, speak, stopSpeaking, clearGenTimer]);

  // Heartbeat
  useEffect(() => {
    if (status !== "online") return;
    const id = setInterval(() => {
      const socket = wsRef.current;
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "ping" }));
      }
    }, HEARTBEAT_INTERVAL_MS);
    return () => clearInterval(id);
  }, [status]);

  // Auto scroll
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const sendViaRest = useCallback(
    async (text: string, assistantId: string) => {
      try {
        let current = sessionIdRef.current;
        if (!current) {
          const res = await fetch("/api/proxy/conversation/sessions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          });
          if (!res.ok) throw new Error(`Falha ao criar sessão (${res.status})`);
          const session = (await res.json()) as ConversationSession;
          current = session.session_id;
          sessionIdRef.current = current;
          setSessionId(current);
        }

        const res = await fetch(
          `/api/proxy/conversation/sessions/${current}/messages`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
          }
        );
        if (!res.ok) throw new Error(`Falha ao enviar mensagem (${res.status})`);
        const data = (await res.json()) as ConversationMessageResponse;

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  status: "done",
                  content: data.text,
                  model: data.model,
                  latency_ms: data.latency_ms,
                }
              : m
          )
        );
      } catch (err) {
        const detail =
          err instanceof Error ? err.message : "Falha na comunicação com o backend";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, status: "error", content: detail }
              : m
          )
        );
      } finally {
        clearGenTimer();
        sendingRef.current = false;
        pendingAssistantRef.current = null;
        setSending(false);
        setThinking(false);
      }
    },
    [clearGenTimer]
  );

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || sendingRef.current) return;

      sendingRef.current = true;
      setSending(true);
      setThinking(true);
      hasUserMessageRef.current = true;
      setAvatarState("thinking");

      const userMsg: ChatViewMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmed,
        status: "done",
      };
      const assistantMsg: ChatViewMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: "",
        status: "streaming",
      };
      pendingAssistantRef.current = assistantMsg.id;

      setMessages((prev) => [...prev, userMsg, assistantMsg]);

      // Watchdog: se não chegar resposta em 90s, marca como erro (evita chat travado)
      clearGenTimer();
      genTimerRef.current = setTimeout(() => {
        if (!sendingRef.current) return;
        sendingRef.current = false;
        pendingAssistantRef.current = null;
        setSending(false);
        setThinking(false);
        setAvatarState("idle");
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? {
                  ...m,
                  status: "error",
                  content:
                    "O NEGÃO demorou para responder. Tente novamente.",
                }
              : m
          )
        );
      }, 90_000);

      const socket = wsRef.current;
      if (socket && socket.readyState === WebSocket.OPEN) {
        try {
          socket.send(
            JSON.stringify({
              type: "chat",
              text: trimmed,
              session_id: sessionIdRef.current,
            })
          );
        } catch {
          await sendViaRest(trimmed, assistantMsg.id);
        }
      } else {
        await sendViaRest(trimmed, assistantMsg.id);
      }
    },
    [sendViaRest, setAvatarState, clearGenTimer]
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const text = input;
      if (!text.trim() || sendingRef.current) return;
      setInput("");
      void sendMessage(text);
    },
    [input, sendMessage]
  );

  const resetConversation = useCallback(() => {
    clearGenTimer();
    setMessages([]);
    sendingRef.current = false;
    pendingAssistantRef.current = null;
    setSending(false);
    setThinking(false);
    const socket = wsRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({ type: "reset", session_id: sessionIdRef.current })
      );
    }
    sessionIdRef.current = null;
    setSessionId(null);
    setAvatarState("idle");
    stopSpeaking();
  }, [setAvatarState, stopSpeaking, clearGenTimer]);

  const copyMessage = useCallback(async (id: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      toast({ title: "Não foi possível copiar", variant: "destructive" });
    }
  }, [toast]);

  const regenerate = useCallback(
    async (messageId: string) => {
      if (sendingRef.current) return;
      const idx = messages.findIndex((m) => m.id === messageId);
      if (idx < 0) return;
      const prevUser = [...messages.slice(0, idx)].reverse().find((m) => m.role === "user");
      if (!prevUser) return;
      const userIdx = messages.findIndex((m) => m.id === prevUser.id);
      if (userIdx < 0) return;

      // Remove resposta antiga + pergunta (sendMessage re-adiciona ambos)
      setMessages(messages.slice(0, userIdx));
      await sendMessage(prevUser.content);
      setRegenMessageId(null);
    },
    [messages, sendMessage]
  );

  // Recording
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      recordingSecondsRef.current = 0;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const form = new FormData();
        form.append("file", blob, "recording.webm");
        try {
          const res = await fetch("/api/proxy/voice/transcribe", {
            method: "POST",
            body: form,
          });
          if (!res.ok) throw new Error("Transcrição falhou");
          const data = (await res.json()) as { text: string };
          if (data.text) {
            setInput(data.text);
          }
        } catch (e) {
          console.warn("Transcribe failed:", e);
        } finally {
          stream.getTracks().forEach((t) => t.stop());
        }
      };

      recorder.start(100);
      setRecording(true);
      setAvatarState("listening");
      recordingTimerRef.current = setInterval(() => {
        recordingSecondsRef.current += 1;
      }, 1000);
    } catch (e) {
      console.warn("Mic access denied:", e);
    }
  }, [setAvatarState]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      setRecording(false);
      setAvatarState("idle");
    }
  }, [recording, setAvatarState]);

  const toggleMic = useCallback(() => {
    if (recording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [recording, startRecording, stopRecording]);

  const toggleTtsMuted = useCallback(() => {
    setTtsMuted((prev) => !prev);
  }, []);

  const stopGeneration = useCallback(() => {
    clearGenTimer();
    sendingRef.current = false;
    pendingAssistantRef.current = null;
    setSending(false);
    setThinking(false);
    setAvatarState("idle");
    stopSpeaking();
    setMessages((prev) =>
      prev.map((m) =>
        m.role === "assistant" && m.status === "streaming"
          ? {
              ...m,
              status: "done",
              content: m.content.trim() || "*(geração interrompida)*",
            }
          : m
      )
    );
  }, [clearGenTimer, setAvatarState, stopSpeaking]);

  const loadSession = useCallback(async (sid: string) => {
    try {
      const res = await fetch(`/api/proxy/conversation/sessions/${sid}/messages`);
      if (!res.ok) return;
      const data = (await res.json()) as { messages: { role: string; content: string }[] };
      setMessages(
        data.messages.map((m, i) => ({
          id: `${m.role}-${i}-${sid}`,
          role: m.role as "user" | "assistant",
          content: m.content,
          status: "done",
        }))
      );
      sessionIdRef.current = sid;
      setSessionId(sid);
      setMessages((prev) => prev);
    } catch (e) {
      console.warn("Load session failed:", e);
    }
  }, []);

  const renameSession = useCallback(async (sid: string, name: string) => {
    try {
      const res = await fetch(`/api/proxy/conversation/sessions/${sid}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        setEditingSession(null);
        fetchSessions();
        toast({ title: "Sessão renomeada", variant: "success" });
      } else {
        throw new Error("Falha ao renomear");
      }
    } catch (e) {
      toast({ title: "Erro", description: String(e), variant: "destructive" });
    }
  }, [fetchSessions, toast]);

  const deleteSession = useCallback(async (sid: string) => {
    if (!confirm("Tem certeza que quer excluir esta conversa?")) return;
    try {
      const res = await fetch(`/api/proxy/conversation/sessions/${sid}`, {
        method: "DELETE",
      });
      if (res.ok) {
        fetchSessions();
        toast({ title: "Conversa excluída", variant: "success" });
      } else {
        throw new Error("Falha ao excluir");
      }
    } catch (e) {
      toast({ title: "Erro", description: String(e), variant: "destructive" });
    }
  }, [fetchSessions, toast]);

  const meta = STATUS_META[status];
  const StatusIcon = meta.icon;

  return (
    <div className="glass flex h-[calc(100dvh-16rem)] min-h-0 flex-col overflow-hidden rounded-2xl sm:min-h-[480px]">
      <header className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-4">
        <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#00D4FF] shadow-[0_0_24px_-6px_rgba(0,212,255,0.7)]">
          <MessageSquare className="size-4 text-[#05070B]" strokeWidth={2.2} />
        </div>
        <div className="leading-tight">
          <h2 className="text-sm font-semibold tracking-wide text-[#F8FAFC]">
            Conversa com o NEGÃO
          </h2>
          <p className="font-mono-data text-[10px] uppercase tracking-widest text-[#94A3B8]">
            {thinking
              ? "pensando…"
              : sessionId
                ? `sessão ${sessionId.slice(0, 8)}…`
                : "aguardando sessão"}
          </p>
        </div>

        <span className="glass ml-auto flex items-center gap-2 rounded-full px-3 py-1.5">
          <StatusIcon
            className={`size-3.5 ${meta.spinning ? "animate-spin" : ""}`}
            style={{ color: meta.color }}
          />
          <span
            className="font-mono-data text-[10px] uppercase tracking-widest"
            style={{ color: meta.color }}
          >
            {meta.label}
          </span>
        </span>

        <button
          type="button"
          onClick={() => setHistoryOpen(!historyOpen)}
          className="glass glass-hover flex size-9 shrink-0 items-center justify-center rounded-xl text-[#94A3B8] hover:text-[#00D4FF]"
          aria-label="Histórico"
          title="Histórico"
        >
          <History className="size-4" />
        </button>

        <button
          type="button"
          onClick={toggleTtsMuted}
          className={`glass glass-hover flex size-9 shrink-0 items-center justify-center rounded-lg text-[#00D4FF] hover:bg-[var(--accent-muted)]`}
          aria-label={ttsMuted ? "Ativar voz do NEGÃO" : "Mutar voz do NEGÃO"}
          title={ttsMuted ? "Ativar voz" : "Mutar voz"}
        >
          {ttsMuted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
        </button>

        <button
          type="button"
          onClick={resetConversation}
          className="glass glass-hover flex size-9 shrink-0 items-center justify-center rounded-xl text-[#94A3B8] hover:text-[#00D4FF]"
          aria-label="Nova conversa"
          title="Nova conversa"
        >
          <RotateCcw className="size-4" />
        </button>
      </header>

      <div className="flex-1 overflow-hidden">
        <div className="flex h-full">
          {/* History sidebar */}
          <div
            className={`transition-all duration-300 ease-in-out ${
              historyOpen ? "w-64" : "w-0"
            }`}
            aria-hidden={!historyOpen}
          >
            {historyOpen && (
              <div className="flex h-full flex-col overflow-y-auto border-r border-white/[0.06] p-3">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="font-mono-data text-[10px] uppercase tracking-wider text-[var(--text-secondary)]">Histórico</h3>
                  <button
                    onClick={() => {
                      const res = window.confirm("Iniciar nova conversa?");
                      if (res) resetConversation();
                    }}
                    className="text-[var(--accent)] hover:text-[var(--accent-glow)]"
                  >
                    <MessageSquare className="size-3.5" />
                  </button>
                </div>
                <div className="space-y-1 overflow-y-auto">
                  {sessions.map((s) => (
                    <div key={s.session_id} className="group relative">
                      <button
                        onClick={() => loadSession(s.session_id)}
                        className="w-full text-left rounded-lg p-2 text-sm hover:bg-white/[0.03] transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div className="truncate font-medium text-[var(--text-primary)]">
                            {s.name || s.session_id.slice(0, 8)}
                          </div>
                          <span className="text-[var(--text-secondary)] text-xs">
                            {s.message_count}m
                          </span>
                        </div>
                        <p className="font-mono-data text-[9px] text-[var(--text-secondary)] truncate">
                          {s.updated_at ? new Date(s.updated_at).toLocaleTimeString() : ""}
                        </p>
                      </button>
                      {editingSession === s.session_id ? (
                        <div className="mt-1 flex items-center gap-1">
                          <input
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            onBlur={() => {
                              if (editingName.trim()) renameSession(s.session_id, editingName.trim());
                              else setEditingSession(null);
                            }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") renameSession(s.session_id, editingName.trim());
                              if (e.key === "Escape") setEditingSession(null);
                            }}
                            className="flex-1 bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-2 py-1 text-xs text-[var(--text-primary)] outline-none"
                            autoFocus
                          />
                          <button
                            onClick={() => {
                              if (editingName.trim()) renameSession(s.session_id, editingName.trim());
                              else setEditingSession(null);
                            }}
                            className="p-0.5 text-[var(--color-ok)]"
                          >
                            <Check className="size-3" />
                          </button>
                          <button
                            onClick={() => setEditingSession(null)}
                            className="p-0.5 text-[var(--color-danger)]"
                          >
                            <X className="size-3" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => {
                            setEditingSession(s.session_id);
                            setEditingName(s.name || "");
                          }}
                          className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 p-0.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                          title="Renomear"
                        >
                          <Edit3 className="size-3" />
                        </button>
                      )}
                      <button
                        onClick={() => deleteSession(s.session_id)}
                        className="absolute bottom-1 right-1 opacity-0 group-hover:opacity-100 p-0.5 text-[var(--color-danger)] hover:text-red-400"
                        title="Excluir"
                      >
                        <Trash2 className="size-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Chat messages */}
          <div
            role="log"
            aria-live="polite"
            className="flex-1 space-y-4 overflow-y-auto px-5 py-5"
          >
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
                <div className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[#3B82F6]/20 to-[#00D4FF]/20 ring-1 ring-white/10">
                  <MessageSquare className="size-6 text-[#00D4FF]" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#E2E8F0]">
                    Fala, chefe.
                  </p>
                  <p className="mt-1 text-sm text-[#64748B]">
                    Pergunta qualquer coisa… a conexão é em tempo real.
                  </p>
                </div>
                <PromptSuggestions
                  onSelect={(prompt) => {
                    setInput(prompt);
                  }}
                />
              </div>
            )}

            {messages.map((m) =>
              m.role === "user" ? (
                <div key={m.id} className="flex justify-end">
                  <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-[#3B82F6]/15 px-4 py-2.5 text-sm text-[#E2E8F0] shadow-[0_0_20px_-8px_rgba(59,130,246,0.5)] ring-1 ring-[#3B82F6]/25">
                    {m.content}
                  </div>
                </div>
              ) : (
                <div key={m.id} className="group/message flex items-start gap-3">
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#00D4FF] text-xs font-bold text-[#05070B] shadow-[0_0_16px_-4px_rgba(0,212,255,0.6)]">
                    N
                  </div>
                  <div className="glass max-w-[85%] rounded-2xl rounded-tl-md px-4 py-2.5">
                    {m.status === "streaming" ? (
                      m.content ? (
                        <div className="text-sm whitespace-pre-wrap break-words text-[#E2E8F0]">
                          <Markdown text={m.content} />
                          <span className="ml-1 inline-block h-3.5 w-1.5 animate-pulse rounded-sm bg-[#00D4FF] align-middle" />
                        </div>
                      ) : (
                        <TypingIndicator />
                      )
                    ) : m.status === "error" ? (
                      <p className="text-sm whitespace-pre-wrap break-words text-[#F87171]">
                        {m.content}
                      </p>
                    ) : (
                      <>
                        <div className="break-words">
                          <Markdown text={m.content} />
                        </div>
                        {(m.model !== undefined || m.latency_ms !== undefined) && (
                          <div className="mt-2 flex items-center gap-3 font-mono-data text-[10px] text-[#64748B]">
                            {m.model !== undefined && (
                              <span className="text-[#00D4FF]">{m.model}</span>
                            )}
                            {m.latency_ms !== undefined && (
                              <span>{m.latency_ms}ms</span>
                            )}
                          </div>
                        )}
                        <div className="mt-2 flex items-center gap-1 opacity-0 transition-opacity group-hover/message:opacity-100">
                          <button
                            type="button"
                            onClick={() => void copyMessage(m.id, m.content)}
                            className="flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] text-[#64748B] transition-colors hover:bg-white/[0.04] hover:text-[#00D4FF]"
                            title="Copiar resposta"
                          >
                            {copiedId === m.id ? (
                              <Check className="size-3 text-[#22C55E]" />
                            ) : (
                              <Copy className="size-3" />
                            )}
                            {copiedId === m.id ? "copiado" : "copiar"}
                          </button>
                          <button
                            type="button"
                            onClick={() => void regenerate(m.id)}
                            disabled={sending || regenMessageId !== null}
                            className="flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] text-[#64748B] transition-colors hover:bg-white/[0.04] hover:text-[#00D4FF] disabled:cursor-not-allowed disabled:opacity-40"
                            title="Gerar nova resposta"
                          >
                            <RefreshCw
                              className={`size-3 ${
                                regenMessageId === m.id ? "animate-spin" : ""
                              }`}
                            />
                            regerar
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )
            )}
            <div ref={endRef} />
          </div>
        </div>
      </div>

      <footer className="border-t border-white/[0.06] p-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <form
          onSubmit={handleSubmit}
          className="glass flex items-end gap-2 rounded-xl px-4 py-2"
        >
          <button
            type="button"
            onClick={toggleMic}
            disabled={sending}
            className={`glass glass-hover mb-1 flex size-9 shrink-0 items-center justify-center rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
              recording
                ? "bg-[var(--color-danger)]/20 text-[var(--color-danger)] animate-pulse"
                : "text-[#00D4FF] hover:bg-[var(--accent-muted)]"
            }`}
            aria-label={recording ? "Parar gravação" : "Gravar áudio"}
            title={recording ? `Parar gravação (${recordingSecondsRef.current}s)` : "Gravar áudio"}
          >
            {recording ? <MicOff className="size-4" /> : <Mic className="size-4" />}
          </button>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              autoResizeTextarea(e.target);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                const form = e.currentTarget.form;
                if (form) {
                  form.requestSubmit();
                }
              }
            }}
            rows={1}
            placeholder="Fala, chefe…  (Enter envia, Shift+Enter quebra linha)"
            className="max-h-32 min-h-[36px] flex-1 resize-none overflow-y-auto bg-transparent py-2 text-sm text-[#F8FAFC] outline-none placeholder:text-[#64748B]"
          />
          <button
            type="button"
            onClick={stopGeneration}
            disabled={!sending}
            className="glass glass-hover mb-1 flex size-9 shrink-0 items-center justify-center rounded-lg text-[#F59E0B] transition-colors hover:bg-[var(--color-warn)]/10 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Parar geração"
            title="Parar geração"
          >
            <Square className="size-3.5 fill-current" />
          </button>
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="glass glass-hover mb-1 flex size-9 shrink-0 items-center justify-center rounded-lg text-[#00D4FF] disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Enviar mensagem"
          >
            {sending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Send className="size-4" />
            )}
          </button>
        </form>
        <p className="mt-2 text-center font-mono-data text-[10px] uppercase tracking-widest text-[var(--text-secondary)]">
          Enter envia · Shift+Enter quebra linha · respostas podem conter formatação
        </p>
      </footer>
    </div>
  );
}
