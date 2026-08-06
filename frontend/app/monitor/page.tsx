"use client";

import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle2,
  Database,
  MemoryStick,
  MessageSquareText,
  Mic,
  Network,
  Radio,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
  Terminal,
  Users,
  Volume2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type {
  BrainRouterInfo,
  BrainStatus,
  ConversationSession,
  ConversationStatus,
  DatabaseStatus,
  EventsStatus,
  Healthz,
  MemoryStatus,
  Readyz,
  SecurityStatus,
  VoiceStatus,
} from "@/lib/types";

const POLL_MS = 5000;

type SnapshotKey =
  | "brain"
  | "router"
  | "convStatus"
  | "sessions"
  | "voice"
  | "memory"
  | "database"
  | "events"
  | "security"
  | "healthz"
  | "readyz"
  | "logs";

interface Snapshot {
  brain: BrainStatus | null;
  router: BrainRouterInfo | null;
  convStatus: ConversationStatus | null;
  sessions: ConversationSession[] | null;
  voice: VoiceStatus | null;
  memory: MemoryStatus | null;
  database: DatabaseStatus | null;
  events: EventsStatus | null;
  security: SecurityStatus | null;
  healthz: Healthz | null;
  readyz: Readyz | null;
  logs: string[] | null;
  errors: Partial<Record<SnapshotKey, string>>;
  fetchedAt: number;
}

const EMPTY_SNAPSHOT: Snapshot = {
  brain: null,
  router: null,
  convStatus: null,
  sessions: null,
  voice: null,
  memory: null,
  database: null,
  events: null,
  security: null,
  healthz: null,
  readyz: null,
  logs: null,
  errors: {},
  fetchedAt: 0,
};

interface FetchResult<T> {
  value: T | null;
  error: string | null;
}

async function fetchJson<T>(url: string): Promise<FetchResult<T>> {
  try {
    const res = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(12_000) });
    if (!res.ok) return { value: null, error: `HTTP ${res.status}` };
    return { value: (await res.json()) as T, error: null };
  } catch {
    return { value: null, error: "sem resposta" };
  }
}

async function fetchLogs(): Promise<FetchResult<string[]>> {
  try {
    const res = await fetch("/api/proxy/monitoring/logs", {
      cache: "no-store",
      signal: AbortSignal.timeout(12_000),
    });
    if (!res.ok) return { value: null, error: `HTTP ${res.status}` };
    const body = (await res.json()) as unknown;
    if (Array.isArray(body)) return { value: body as string[], error: null };
    if (
      body !== null &&
      typeof body === "object" &&
      Array.isArray((body as { lines?: unknown }).lines)
    ) {
      return { value: (body as { lines: string[] }).lines, error: null };
    }
    return { value: null, error: "formato inesperado" };
  } catch {
    return { value: null, error: "sem resposta" };
  }
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: LucideIcon;
  children: ReactNode;
}) {
  const Icon = icon;
  return (
    <section className="animate-fade-up space-y-4">
      <div className="flex items-center gap-2">
        <Icon className="size-4 text-[#00D4FF]" />
        <h2 className="font-mono-data text-[11px] font-semibold tracking-[0.3em] text-[#F8FAFC]">
          {title}
        </h2>
        <span className="h-px flex-1 bg-white/[0.06]" />
      </div>
      <div className="grid grid-cols-12 gap-4">{children}</div>
    </section>
  );
}

function Panel({
  title,
  icon,
  badge,
  error,
  children,
  className = "",
}: {
  title: string;
  icon: LucideIcon;
  badge?: ReactNode;
  error?: string | null;
  children: ReactNode;
  className?: string;
}) {
  const Icon = icon;
  return (
    <div className={`glass glass-hover rounded-2xl p-4 ${className}`}>
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className="size-3.5 text-[#00D4FF]" />
          <h3 className="font-mono-data text-[10px] font-semibold tracking-[0.25em] text-[#94A3B8]">
            {title}
          </h3>
        </div>
        {badge ?? null}
      </div>
      {error ? (
        <p className="font-mono-data text-[10px] text-[#EF4444]">ERRO: {error}</p>
      ) : (
        children
      )}
    </div>
  );
}

function StatusBadge({ ok, label }: { ok: boolean; label?: string }) {
  const cls = ok
    ? "text-[#22C55E] bg-[#22C55E]/10 ring-[#22C55E]/30"
    : "text-[#EF4444] bg-[#EF4444]/10 ring-[#EF4444]/30";
  const dot = ok ? "bg-[#22C55E]" : "bg-[#EF4444]";
  return (
    <span
      className={`flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mono-data text-[9px] font-semibold tracking-wider ring-1 ${cls}`}
    >
      <span className={`size-1.5 rounded-full ${dot}`} style={{ boxShadow: "0 0 8px currentColor" }} />
      {label ?? (ok ? "OK" : "FALHA")}
    </span>
  );
}

function ModeBadge({ mode }: { mode: string }) {
  const upper = mode.toUpperCase();
  const isLocal = mode.toLowerCase() === "local";
  const isNvidia = mode.toLowerCase() === "nvidia";
  const cls = isLocal
    ? "text-[#22C55E] bg-[#22C55E]/10 ring-[#22C55E]/30"
    : isNvidia
      ? "text-[#00D4FF] bg-[#00D4FF]/10 ring-[#00D4FF]/30"
      : "text-[#94A3B8] bg-white/5 ring-white/10";
  const dot = isLocal ? "bg-[#22C55E]" : isNvidia ? "bg-[#00D4FF]" : "bg-[#94A3B8]";
  return (
    <span
      className={`flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mono-data text-[9px] font-semibold tracking-wider ring-1 ${cls}`}
    >
      <span className={`size-1.5 rounded-full ${dot}`} style={{ boxShadow: "0 0 8px currentColor" }} />
      {upper}
    </span>
  );
}

function InfoRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "ok" | "warn" | "danger";
}) {
  const color =
    tone === "danger"
      ? "text-[#EF4444]"
      : tone === "warn"
        ? "text-[#F59E0B]"
        : "text-[#F8FAFC]";
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="shrink-0 font-mono-data text-[10px] tracking-wider text-[#94A3B8]">
        {label}
      </span>
      <span title={value} className={`max-w-[60%] truncate font-mono-data text-[11px] font-semibold ${color}`}>
        {value}
      </span>
    </div>
  );
}

function EmptyData() {
  return <p className="font-mono-data text-[10px] text-[#64748B]">Sem dados.</p>;
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function BrainSection({ snapshot }: { snapshot: Snapshot }) {
  const { brain, router } = snapshot;
  const mode = brain?.mode ?? router?.mode ?? null;
  const primary = brain?.primary_model ?? router?.primary_model ?? null;
  const fallback = brain?.fallback_model ?? router?.fallback_model ?? null;
  const modelError =
    brain === null && router === null
      ? (snapshot.errors.brain ?? snapshot.errors.router)
      : null;

  return (
    <Section title="CÉREBRO" icon={Brain}>
      <Panel
        title="MODELO ATIVO"
        icon={Sparkles}
        className="col-span-12 lg:col-span-6"
        badge={
          mode ? <ModeBadge mode={mode} /> : <StatusBadge ok={false} label="SEM DADOS" />
        }
        error={modelError}
      >
        <p className="truncate text-lg font-semibold text-[#F8FAFC]">{primary ?? "—"}</p>
        <div className="mt-2.5 space-y-1.5">
          <InfoRow label="FALLBACK" value={fallback ?? "—"} />
          <InfoRow label="MODO" value={mode ? mode.toUpperCase() : "—"} />
          {brain ? (
            <>
              <InfoRow label="RETRIES" value={String(brain.retry_attempts)} />
              <InfoRow
                label="CIRCUIT FAILURES"
                value={String(brain.circuit_failures)}
                tone={brain.circuit_failures > 0 ? "warn" : "ok"}
              />
              <InfoRow label="CACHE TTL" value={`${brain.cache_ttl_seconds}s`} />
            </>
          ) : null}
        </div>
      </Panel>

      <Panel
        title="ROTEADOR"
        icon={Network}
        className="col-span-12 lg:col-span-6"
        badge={<StatusBadge ok={router !== null} />}
        error={snapshot.errors.router}
      >
        {router ? (
          <div className="space-y-1.5">
            <InfoRow
              label="INSTANCE ROUTER"
              value={router.instance_router ? "ATIVO" : "INATIVO"}
              tone={router.instance_router ? "ok" : "warn"}
            />
            <InfoRow label="MODO" value={router.mode.toUpperCase()} />
            <InfoRow label="PRIMARY" value={router.primary_model} />
            <InfoRow label="FALLBACK" value={router.fallback_model} />
          </div>
        ) : (
          <EmptyData />
        )}
      </Panel>
    </Section>
  );
}

function ConversationSection({ snapshot }: { snapshot: Snapshot }) {
  const { convStatus, sessions } = snapshot;
  const total = convStatus?.sessions ?? sessions?.length ?? null;
  const degraded = convStatus?.degraded ?? false;
  const totalMessages =
    sessions === null
      ? null
      : sessions.reduce((acc, s) => acc + (s.message_count ?? 0), 0);
  const lastSession =
    sessions === null || sessions.length === 0
      ? null
      : [...sessions].sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0];

  return (
    <Section title="CONVERSAÇÃO" icon={MessageSquareText}>
      <Panel
        title="RESUMO"
        icon={Activity}
        className="col-span-12 md:col-span-6 lg:col-span-3"
        badge={
          convStatus ? (
            <StatusBadge ok={!degraded} label={degraded ? "DEGRADADO" : "OK"} />
          ) : undefined
        }
        error={snapshot.errors.convStatus}
      >
        <p className="text-3xl font-bold text-[#F8FAFC]">{total === null ? "—" : total}</p>
        <p className="mt-1 font-mono-data text-[9px] tracking-[0.25em] text-[#94A3B8]">
          SESSÕES ATIVAS
        </p>
        <div className="mt-3 border-t border-white/[0.05] pt-2.5">
          <InfoRow
            label="MENSAGENS"
            value={totalMessages === null ? "—" : String(totalMessages)}
          />
        </div>
      </Panel>

      <Panel
        title="SESSÃO MAIS RECENTE"
        icon={Sparkles}
        className="col-span-12 md:col-span-6 lg:col-span-3"
        badge={lastSession ? <StatusBadge ok label="ATIVA" /> : undefined}
        error={snapshot.errors.sessions}
      >
        {lastSession ? (
          <div className="space-y-1.5">
            <p className="truncate font-mono-data text-[11px] font-semibold text-[#00D4FF]">
              {lastSession.name || lastSession.session_id.slice(0, 12)}
            </p>
            <InfoRow label="MENSAGENS" value={String(lastSession.message_count)} />
            <InfoRow label="ATUALIZADO" value={formatWhen(lastSession.updated_at)} />
            <Link
              href={`/conversa?session=${encodeURIComponent(lastSession.session_id)}`}
              className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-[#3B82F6]/40 bg-[#3B82F6]/10 px-3 py-1.5 text-xs font-medium text-[#93C5FD] transition-colors hover:bg-[#3B82F6]/20 hover:text-[#DBEAFE]"
            >
              <MessageSquareText className="size-3.5" />
              Abrir no chat
            </Link>
          </div>
        ) : (
          <EmptyData />
        )}
      </Panel>

      <Panel
        title="SESSÕES"
        icon={Users}
        className="col-span-12 lg:col-span-6"
        badge={sessions ? <StatusBadge ok label="OK" /> : undefined}
        error={snapshot.errors.sessions}
      >
        {sessions === null ? (
          <EmptyData />
        ) : sessions.length === 0 ? (
          <p className="font-mono-data text-[10px] text-[#64748B]">
            Nenhuma sessão registrada.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="font-mono-data text-[9px] tracking-[0.2em] text-[#64748B]">
                  <th className="pb-2 pr-4 font-semibold">SESSION ID</th>
                  <th className="pb-2 pr-4 font-semibold">USUÁRIO</th>
                  <th className="pb-2 pr-4 font-semibold">MENSAGENS</th>
                  <th className="pb-2 font-semibold">ATUALIZADO</th>
                </tr>
              </thead>
              <tbody>
                {[...sessions]
                  .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
                  .map((s) => (
                    <tr key={s.session_id} className="border-t border-white/[0.04]">
                      <td title={s.session_id} className="max-w-[240px] truncate py-2 pr-4 font-mono-data text-[10px] text-[#00D4FF]">
                        {s.session_id}
                      </td>
                      <td className="py-2 pr-4 font-mono-data text-[10px] text-[#94A3B8]">
                        {s.user_id ?? "—"}
                      </td>
                      <td className="py-2 pr-4 font-mono-data text-[10px] text-[#F8FAFC]">
                        {s.message_count}
                      </td>
                      <td className="py-2 font-mono-data text-[10px] text-[#94A3B8]">
                        {formatWhen(s.updated_at)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </Section>
  );
}

function VoiceSection({ snapshot }: { snapshot: Snapshot }) {
  const voice = snapshot.voice;
  return (
    <Section title="VOZ" icon={Mic}>
      <Panel
        title="STT"
        icon={Radio}
        className="col-span-12 md:col-span-6"
        badge={
          <StatusBadge
            ok={voice?.stt_available === true}
            label={voice?.stt_available ? "DISPONÍVEL" : "INDISPONÍVEL"}
          />
        }
        error={snapshot.errors.voice}
      >
        {voice ? <InfoRow label="MODELO" value={voice.stt_model || "—"} /> : <EmptyData />}
      </Panel>
      <Panel
        title="TTS"
        icon={Volume2}
        className="col-span-12 md:col-span-6"
        badge={
          <StatusBadge
            ok={voice?.tts_available === true}
            label={voice?.tts_available ? "DISPONÍVEL" : "INDISPONÍVEL"}
          />
        }
        error={snapshot.errors.voice}
      >
        {voice ? <InfoRow label="VOZ" value={voice.tts_voice || "—"} /> : <EmptyData />}
      </Panel>
    </Section>
  );
}

function InfraSection({ snapshot }: { snapshot: Snapshot }) {
  const { database, memory, events, security, healthz, readyz, logs } = snapshot;
  const streams = events?.streams ? Object.keys(events.streams).length : null;
  const handlers = events?.handlers ? events.handlers.length : null;
  const deliveries = events?.deliveries ? Object.keys(events.deliveries).length : null;
  const securityOk = security?.authenticated === true || security?.status === "ok";

  return (
    <Section title="INFRA" icon={Server}>
      <Panel
        title="DATABASE"
        icon={Database}
        className="col-span-12 md:col-span-6 lg:col-span-4"
        badge={<StatusBadge ok={database?.connected === true} />}
        error={snapshot.errors.database}
      >
        {database ? (
          <div className="space-y-1.5">
            <InfoRow
              label="CONEXÃO"
              value={database.connected ? "CONECTADO" : "DESCONECTADO"}
              tone={database.connected ? "ok" : "danger"}
            />
            <InfoRow label="ENGINE" value={database.engine_url} />
            <InfoRow label="CONEXÕES ATIVAS" value={String(database.active_connections)} />
            <InfoRow label="DETALHE" value={database.detail} />
          </div>
        ) : (
          <EmptyData />
        )}
      </Panel>

      <Panel
        title="MEMÓRIA"
        icon={MemoryStick}
        className="col-span-12 md:col-span-6 lg:col-span-4"
        badge={<StatusBadge ok={memory?.redis_connected === true} />}
        error={snapshot.errors.memory}
      >
        {memory ? (
          <InfoRow
            label="REDIS STM"
            value={memory.redis_connected ? "CONECTADO" : "DEGRADADO"}
            tone={memory.redis_connected ? "ok" : "danger"}
          />
        ) : (
          <EmptyData />
        )}
      </Panel>

      <Panel
        title="EVENTOS"
        icon={Radio}
        className="col-span-12 md:col-span-6 lg:col-span-4"
        badge={<StatusBadge ok={events !== null} />}
        error={snapshot.errors.events}
      >
        {events ? (
          <div className="space-y-1.5">
            {streams !== null ? <InfoRow label="STREAMS" value={String(streams)} /> : null}
            {handlers !== null ? <InfoRow label="HANDLERS" value={String(handlers)} /> : null}
            {deliveries !== null ? <InfoRow label="DELIVERIES" value={String(deliveries)} /> : null}
            {streams === null && handlers === null && deliveries === null ? <EmptyData /> : null}
          </div>
        ) : (
          <EmptyData />
        )}
      </Panel>

      <Panel
        title="SEGURANÇA"
        icon={ShieldCheck}
        className="col-span-12 md:col-span-6 lg:col-span-4"
        badge={<StatusBadge ok={securityOk} />}
        error={snapshot.errors.security}
      >
        {security ? (
          <div className="space-y-1.5">
            <InfoRow label="AUTORIZAÇÃO" value={security.authorization_level} />
            <InfoRow
              label="AUTHENTICATED"
              value={security.authenticated ? "SIM" : "NÃO"}
              tone={security.authenticated ? "ok" : "warn"}
            />
            <InfoRow label="PRINCIPAL" value={security.principal} />
          </div>
        ) : (
          <EmptyData />
        )}
      </Panel>

      <Panel
        title="HEALTHZ"
        icon={Activity}
        className="col-span-12 md:col-span-6 lg:col-span-4"
        badge={<StatusBadge ok={healthz?.status === "alive"} />}
        error={snapshot.errors.healthz}
      >
        {healthz ? (
          <InfoRow
            label="STATUS"
            value={String(healthz.status)}
            tone={healthz.status === "alive" ? "ok" : "danger"}
          />
        ) : (
          <EmptyData />
        )}
      </Panel>

      <Panel
        title="READYZ"
        icon={CheckCircle2}
        className="col-span-12 md:col-span-6 lg:col-span-4"
        badge={<StatusBadge ok={readyz?.status === "ok"} />}
        error={snapshot.errors.readyz}
      >
        {readyz ? (
          <div className="space-y-1.5">
            <InfoRow
              label="STATUS"
              value={String(readyz.status)}
              tone={readyz.status === "ok" ? "ok" : "warn"}
            />
            {Object.keys(readyz.checks).length > 0 ? (
              <div className="space-y-1.5 border-t border-white/[0.05] pt-2">
                {Object.entries(readyz.checks).map(([name, value]) => {
                  const v = value.toLowerCase();
                  const tone = v === "ok" || v === "pass" ? "ok" : v === "fail" ? "danger" : "warn";
                  return <InfoRow key={name} label={name.toUpperCase()} value={value} tone={tone} />;
                })}
              </div>
            ) : null}
          </div>
        ) : (
          <EmptyData />
        )}
      </Panel>

      <Panel
        title="LOGS"
        icon={Terminal}
        className="col-span-12"
        badge={<StatusBadge ok={logs !== null} />}
        error={snapshot.errors.logs}
      >
        {logs === null ? (
          <EmptyData />
        ) : logs.length === 0 ? (
          <p className="font-mono-data text-[10px] text-[#64748B]">Nenhum log registrado.</p>
        ) : (
          <pre className="max-h-64 overflow-auto rounded-xl bg-black/30 p-3 font-mono-data text-[10px] leading-relaxed text-[#94A3B8]">
            {logs.slice(-10).join("\n")}
          </pre>
        )}
      </Panel>
    </Section>
  );
}

export default function MonitorPage() {
  const [snapshot, setSnapshot] = useState<Snapshot>(EMPTY_SNAPSHOT);

  const load = useCallback(async () => {
    const [
      brain,
      router,
      convStatus,
      sessionsRes,
      voice,
      memory,
      database,
      events,
      security,
      healthz,
      readyz,
      logs,
    ] = await Promise.all([
      fetchJson<BrainStatus>("/api/proxy/brain/status"),
      fetchJson<BrainRouterInfo>("/api/proxy/brain/router"),
      fetchJson<ConversationStatus>("/api/proxy/conversation/status"),
      fetchJson<{ sessions: ConversationSession[] }>("/api/proxy/conversation/sessions"),
      fetchJson<VoiceStatus>("/api/proxy/voice/status"),
      fetchJson<MemoryStatus>("/api/proxy/memory/status"),
      fetchJson<DatabaseStatus>("/api/proxy/database/status"),
      fetchJson<EventsStatus>("/api/proxy/events/status"),
      fetchJson<SecurityStatus>("/api/proxy/security/status"),
      fetchJson<Healthz>("/api/proxy/healthz"),
      fetchJson<Readyz>("/api/proxy/readyz"),
      fetchLogs(),
    ]);

    setSnapshot({
      brain: brain.value,
      router: router.value,
      convStatus: convStatus.value,
      sessions: sessionsRes.value?.sessions ?? null,
      voice: voice.value,
      memory: memory.value,
      database: database.value,
      events: events.value,
      security: security.value,
      healthz: healthz.value,
      readyz: readyz.value,
      logs: logs.value,
      errors: {
        brain: brain.error ?? undefined,
        router: router.error ?? undefined,
        convStatus: convStatus.error ?? undefined,
        sessions: sessionsRes.error ?? undefined,
        voice: voice.error ?? undefined,
        memory: memory.error ?? undefined,
        database: database.error ?? undefined,
        events: events.error ?? undefined,
        security: security.error ?? undefined,
        healthz: healthz.error ?? undefined,
        readyz: readyz.error ?? undefined,
        logs: logs.error ?? undefined,
      },
      fetchedAt: Date.now(),
    });
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, POLL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") void load();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [load]);

  const hasData = snapshot.fetchedAt > 0;
  const backendUnreachable = hasData && snapshot.healthz === null;
  const failedCount = Object.values(snapshot.errors).filter((e) => e !== undefined).length;
  const lastSync = hasData
    ? new Date(snapshot.fetchedAt).toLocaleTimeString("pt-BR", { hour12: false })
    : "--:--:--";

  return (
    <main className="mx-auto min-h-dvh max-w-7xl space-y-6 p-5 md:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#00D4FF] shadow-[0_0_24px_-6px_rgba(0,212,255,0.7)]">
            <Server className="size-5 text-[#05070B]" strokeWidth={2.2} />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold tracking-wide text-[#F8FAFC]">
              NEGÃO <span className="text-gradient glow-text">AI</span>
            </p>
            <p className="font-mono-data text-[10px] text-[#94A3B8]">MONITORAMENTO</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="glass flex items-center gap-2 rounded-xl px-3 py-1.5 font-mono-data text-[10px] text-[#94A3B8]">
            <RefreshCw className="size-3 animate-spin-slow text-[#00D4FF]" />
            ATUALIZADO {lastSync}
            {failedCount > 0 ? (
              <span className="text-[#F59E0B]">· {failedCount} FALHA(S)</span>
            ) : null}
          </div>
          <Link
            href="/"
            className="glass glass-hover rounded-xl px-3 py-1.5 font-mono-data text-[10px] text-[#94A3B8] transition-colors hover:text-[#F8FAFC]"
          >
            ← DASHBOARD
          </Link>
        </div>
      </header>

      {backendUnreachable ? (
        <div className="glass flex items-center gap-3 rounded-2xl border-[#EF4444]/40 px-4 py-3">
          <AlertTriangle className="size-4 shrink-0 text-[#EF4444]" />
          <p className="text-sm text-[#EF4444]">
            Backend inacessível — os cards abaixo exibem erro até o serviço voltar.
          </p>
        </div>
      ) : null}

      <BrainSection snapshot={snapshot} />
      <ConversationSection snapshot={snapshot} />
      <VoiceSection snapshot={snapshot} />
      <InfraSection snapshot={snapshot} />
    </main>
  );
}
