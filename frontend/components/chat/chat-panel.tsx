"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Loader2,
  MessageSquare,
  RotateCcw,
  Send,
  Wifi,
  WifiOff,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type {
  ChatViewMessage,
  ConversationMessageResponse,
  ConversationSession,
  WsInfo,
  WsServerMessage,
} from "@/lib/types";

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
  const [status, setStatus] = useState<WsStatus>("conectando");
  const [messages, setMessages] = useState<ChatViewMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [wsBase, setWsBase] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const hasUserMessageRef = useRef(false);
  const sendingRef = useRef(false);
  const endRef = useRef<HTMLDivElement | null>(null);

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
    return () => {
      cancelled = true;
    };
  }, []);

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
          sessionIdRef.current = msg.session_id;
          setSessionId(msg.session_id);
          break;
        case "tokens":
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
                };
                break;
              }
            }
            return copy;
          });
          sendingRef.current = false;
          setSending(false);
          break;
        case "error":
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
          setSending(false);
          break;
        case "pong":
          break;
      }
    };

    const scheduleReconnect = () => {
      if (disposed || hasUserMessageRef.current) {
        setStatus("offline");
        return;
      }
      setStatus("conectando");
      const delay =
        RECONNECT_DELAYS_MS[Math.min(attempt, RECONNECT_DELAYS_MS.length - 1)];
      attempt += 1;
      clearReconnect();
      reconnectTimer = setTimeout(connect, delay);
    };

    const connect = () => {
      if (disposed || hasUserMessageRef.current) return;
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
        if (hasUserMessageRef.current) {
          setStatus("offline");
          return;
        }
        scheduleReconnect();
      };
    };

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
  }, [apiKey, wsBase]);

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
        sendingRef.current = false;
        setSending(false);
      }
    },
    []
  );

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || sendingRef.current) return;

      sendingRef.current = true;
      setSending(true);
      hasUserMessageRef.current = true;

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

      setMessages((prev) => [...prev, userMsg, assistantMsg]);

      const socket = wsRef.current;
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(
          JSON.stringify({
            type: "chat",
            text: trimmed,
            session_id: sessionIdRef.current,
          })
        );
      } else {
        await sendViaRest(trimmed, assistantMsg.id);
      }
    },
    [sendViaRest]
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
    setMessages([]);
    sendingRef.current = false;
    setSending(false);
    const socket = wsRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({ type: "reset", session_id: sessionIdRef.current })
      );
    }
    sessionIdRef.current = null;
    setSessionId(null);
  }, []);

  const meta = STATUS_META[status];
  const StatusIcon = meta.icon;

  return (
    <div className="glass flex h-[calc(100vh-16rem)] min-h-[480px] flex-col overflow-hidden rounded-2xl">
      <header className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-4">
        <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#00D4FF] shadow-[0_0_24px_-6px_rgba(0,212,255,0.7)]">
          <MessageSquare className="size-4 text-[#05070B]" strokeWidth={2.2} />
        </div>
        <div className="leading-tight">
          <h2 className="text-sm font-semibold tracking-wide text-[#F8FAFC]">
            Conversa com o NEGÃO
          </h2>
          <p className="font-mono-data text-[10px] uppercase tracking-widest text-[#94A3B8]">
            {sessionId ? `sessão ${sessionId.slice(0, 8)}…` : "aguardando sessão"}
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
          onClick={resetConversation}
          className="glass glass-hover flex size-9 shrink-0 items-center justify-center rounded-xl text-[#94A3B8] hover:text-[#00D4FF]"
          aria-label="Nova conversa"
          title="Nova conversa"
        >
          <RotateCcw className="size-4" />
        </button>
      </header>

      <div
        role="log"
        aria-live="polite"
        className="flex-1 space-y-4 overflow-y-auto px-5 py-5"
      >
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
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
            <div key={m.id} className="flex items-start gap-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#00D4FF] text-xs font-bold text-[#05070B] shadow-[0_0_16px_-4px_rgba(0,212,255,0.6)]">
                N
              </div>
              <div className="glass max-w-[85%] rounded-2xl rounded-tl-md px-4 py-2.5">
                {m.status === "streaming" ? (
                  <p className="text-sm whitespace-pre-wrap break-words text-[#E2E8F0]">
                    {m.content}
                    <span className="ml-1 inline-block animate-pulse text-[#00D4FF]">
                      …
                    </span>
                  </p>
                ) : m.status === "error" ? (
                  <p className="text-sm whitespace-pre-wrap break-words text-[#F87171]">
                    {m.content}
                  </p>
                ) : (
                  <>
                    <p className="text-sm whitespace-pre-wrap break-words text-[#E2E8F0]">
                      {m.content}
                    </p>
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
                  </>
                )}
              </div>
            </div>
          )
        )}
        <div ref={endRef} />
      </div>

      <footer className="border-t border-white/[0.06] p-4">
        <form
          onSubmit={handleSubmit}
          className="glass flex items-center gap-3 rounded-xl px-4 py-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Fala, chefe…"
            className="flex-1 bg-transparent py-2 text-sm text-[#F8FAFC] outline-none placeholder:text-[#64748B]"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="glass glass-hover flex size-9 shrink-0 items-center justify-center rounded-lg text-[#00D4FF] disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Enviar mensagem"
          >
            {sending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Send className="size-4" />
            )}
          </button>
        </form>
      </footer>
    </div>
  );
}
