"use client";

import {
  Boxes,
  Brain,
  Cloud,
  Database,
  FileText,
  FolderGit2,
  GitBranch,
  HardDrive,
  MemoryStick,
  Monitor,
  Network,
  Server,
  Sparkles,
  Thermometer,
  Timer,
  Wrench,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { BrainStatus, DashboardData } from "@/lib/types";

interface Row {
  label: string;
  icon?: LucideIcon;
  value: string;
  tone?: "ok" | "warn" | "danger";
}

function Card({
  title,
  icon,
  children,
  className = "",
}: {
  title: string;
  icon: LucideIcon;
  children: React.ReactNode;
  className?: string;
}) {
  const Icon = icon;
  return (
    <div className={`glass glass-hover animate-fade-up rounded-2xl p-4 ${className}`}>
      <div className="mb-3 flex items-center gap-2">
        <Icon className="size-3.5 text-[var(--accent)]" />
        <h3 className="font-mono-data text-[10px] font-semibold tracking-[0.25em] text-[var(--text-secondary)]">
          {title}
        </h3>
      </div>
      {children}
    </div>
  );
}

export function SystemCard({ data }: { data: DashboardData | null }) {
  const latencyMs = data?.latency_ms ?? null;
  const rows: Row[] = [
    { label: "CPU", icon: Zap, value: "—", tone: "warn" },
    { label: "RAM", icon: MemoryStick, value: "—", tone: "warn" },
    { label: "GPU", icon: Monitor, value: "—", tone: "warn" },
    { label: "REDE", icon: Network, value: "—", tone: "warn" },
    { label: "DISCO", icon: HardDrive, value: "—", tone: "warn" },
    {
      label: "DOCKER",
      icon: Boxes,
      value: data?.backend_reachable ? "ATIVO" : "INDISPONÍVEL",
      tone: data?.backend_reachable ? "ok" : "warn",
    },
    { label: "TEMPERATURA", icon: Thermometer, value: "—", tone: "warn" },
    {
      label: "LATÊNCIA",
      icon: Timer,
      value: latencyMs === null ? "--ms" : `${latencyMs}ms`,
      tone: latencyMs !== null && latencyMs < 200 ? "ok" : "warn",
    },
  ];

  return (
    <Card title="SISTEMA" icon={Server}>
      <div className="space-y-2.5">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center gap-3">
            {row.icon ? <row.icon className="size-3.5 text-[var(--text-secondary)]" /> : null}
            <span className="flex-1 font-mono-data text-[10px] tracking-wider text-[var(--text-secondary)]">
              {row.label}
            </span>
            <span
              className={`font-mono-data text-[11px] font-semibold ${
                row.tone === "danger"
                  ? "text-[var(--color-danger)]"
                  : row.tone === "warn"
                    ? "text-[var(--color-warn)]"
                    : "text-[var(--color-ok)]"
              }`}
            >
              {row.value}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function ModelCard({ brain }: { brain: BrainStatus | null }) {
  const mode = brain?.mode ?? null;
  const primary = brain?.primary_model ?? "—";
  const fallback = brain?.fallback_model ?? null;
  const circuitFailures = brain?.circuit_failures ?? null;
  const modeLabel =
    mode === "nvidia" ? "● NVIDIA" : mode === "local" ? "● LOCAL" : "● sem dados";
  const modeColor =
    mode === "nvidia" || mode === "local" ? "text-[var(--color-ok)]" : "text-[var(--color-warn)]";
  const rows: Row[] = [
    { label: "FORNECEDOR", value: mode === "local" ? "LOCAL (GPU)" : mode === "nvidia" ? "NVIDIA API" : "—" },
    { label: "FALLBACK MODEL", value: fallback ?? "—" },
    { label: "TEMPO MÉDIO", value: "—" },
    { label: "TOKENS (SESSÃO)", value: "—" },
    { label: "CUSTO (SESSÃO)", value: "—" },
  ];
  if (circuitFailures !== null) {
    rows.push({
      label: "CIRCUIT FAILURES",
      value: String(circuitFailures),
      tone: circuitFailures > 0 ? "warn" : "ok",
    });
  }
  return (
    <Card title="MODELO" icon={Sparkles}>
      <div className="mb-3 flex items-center gap-3">
        <div className="relative flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--color-prime)]/30 to-[var(--accent)]/20 ring-1 ring-[var(--accent)]/30">
          <Brain className="size-4 text-[var(--accent)]" />
        </div>
        <div className="min-w-0 leading-tight">
          <p className="truncate text-sm font-semibold text-[var(--text-primary)]">{primary}</p>
          <p className={`font-mono-data text-[10px] ${modeColor}`}>{modeLabel}</p>
        </div>
      </div>
      <div className="space-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between gap-2">
            <span className="font-mono-data text-[10px] tracking-wider text-[var(--text-secondary)]">
              {row.label}
            </span>
            <span
              title={row.value}
              className={`max-w-[55%] truncate font-mono-data text-[11px] font-semibold ${
                row.tone === "danger"
                  ? "text-[var(--color-danger)]"
                  : row.tone === "warn"
                    ? "text-[var(--color-warn)]"
                    : row.tone === "ok"
                      ? "text-[var(--color-ok)]"
                      : "text-[var(--text-primary)]"
              }`}
            >
              {row.value}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function MemoryCard({ data }: { data: DashboardData | null }) {
  const redisKnown = data?.memory !== null && data?.memory !== undefined;
  const redisOk = data?.memory?.redis_connected === true;
  const rows: Row[] = [
    { label: "CONVERSAS", value: "—" },
    { label: "PROJETOS", value: "—" },
    { label: "DOCUMENTOS", value: "—" },
    { label: "CONHECIMENTO", value: "—" },
    { label: "VETORES", value: "—" },
    { label: "RELACIONAMENTOS", value: "—" },
  ];
  return (
    <Card title="MEMÓRIA" icon={Brain}>
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono-data text-[10px] tracking-wider text-[var(--text-secondary)]">
          REDIS STM
        </span>
        <span
          className={`flex items-center gap-1.5 font-mono-data text-[10px] ${
            redisOk ? "text-[var(--color-ok)]" : "text-[var(--color-warn)]"
          }`}
        >
          <span className="size-1.5 rounded-full bg-current shadow-[0_0_8px_currentColor]" />
          {redisKnown ? (redisOk ? "CONECTADO" : "INDISPONÍVEL") : "SEM DADOS"}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-baseline justify-between gap-2">
            <span className="font-mono-data text-[10px] tracking-wider text-[var(--text-secondary)]">
              {row.label}
            </span>
            <span className="font-mono-data text-[11px] font-semibold text-[var(--text-primary)]">
              {row.value}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function ToolsCard({
  data,
  brain,
}: {
  data: DashboardData | null;
  brain: BrainStatus | null;
}) {
  type ToolStatus = "ok" | "danger" | "warn";
  const statusFor = (known: boolean, ok: boolean): ToolStatus => (known ? (ok ? "ok" : "danger") : "warn");
  const databaseKnown = data?.database !== null && data?.database !== undefined;
  const memoryKnown = data?.memory !== null && data?.memory !== undefined;
  const brainKnown = typeof brain?.mode === "string" && typeof brain?.primary_model === "string";
  const tools: { label: string; icon: LucideIcon; status: ToolStatus }[] = [
    { label: "LLM", icon: Brain, status: statusFor(brainKnown, brainKnown) },
    { label: "GitHub", icon: GitBranch, status: "warn" },
    { label: "Docker", icon: Boxes, status: "warn" },
    { label: "VS Code", icon: FileText, status: "warn" },
    { label: "PostgreSQL", icon: Database, status: statusFor(databaseKnown, data?.database?.connected === true) },
    { label: "Redis", icon: MemoryStick, status: statusFor(memoryKnown, data?.memory?.redis_connected === true) },
    { label: "SSH", icon: Wrench, status: "warn" },
    { label: "Cloudflare", icon: Cloud, status: "warn" },
    { label: "Coolify", icon: Server, status: "warn" },
    { label: "Google Drive", icon: FolderGit2, status: "warn" },
  ];
  return (
    <Card title="FERRAMENTAS" icon={Wrench}>
      <div className="grid grid-cols-3 gap-2">
        {tools.map((tool) => (
          <div
            key={tool.label}
            className="glass glass-hover flex flex-col items-center gap-1.5 rounded-xl px-2 py-2.5"
            title={tool.status === "ok" ? "conectado" : tool.status === "danger" ? "indisponível" : "não verificado"}
          >
            <tool.icon className="size-4 text-[var(--text-primary)]" />
            <span className="max-w-full truncate text-[9px] text-[var(--text-secondary)]">
              {tool.label}
            </span>
            <span
              className={`size-1 rounded-full ${
                tool.status === "ok" ? "bg-[var(--color-ok)]" : tool.status === "danger" ? "bg-[var(--color-danger)]" : "bg-[var(--color-warn)]"
              }`}
              style={{ boxShadow: "0 0 8px currentColor" }}
            />
          </div>
        ))}
      </div>
    </Card>
  );
}

export function Greeting({ data }: { data: DashboardData | null }) {
  const hour = new Date().getHours();
  const period = hour < 6 ? "Boa madrugada" : hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
  const online = data?.healthz?.status === "alive";
  const ready = data?.readyz?.status === "ready";

  return (
    <div className="animate-fade-up text-center">
      <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
        {period}, <span className="text-gradient">Wanderson</span>.
      </h1>
      <p className="mt-2 text-sm text-[var(--text-secondary)]">
        <span className={online ? "text-[var(--color-ok)]" : "text-[var(--color-danger)]"}>
          Sophie está {online ? "online" : "offline"}.
        </span>{" "}
        {ready
          ? "Tudo funcionando normalmente."
          : "Operando com ressalvas em alguns subsistemas."}
      </p>
      <div className="mx-auto mt-3 flex max-w-md flex-wrap items-center justify-center gap-2 font-mono-data text-[10px] text-[var(--text-secondary)]">
        <span className="glass rounded-full px-3 py-1">{data?.backend_reachable ? "DADOS AO VIVO" : "MODO OFFLINE"}</span>
        <span className={`glass rounded-full px-3 py-1 ${ready ? "text-[var(--color-ok)]" : "text-[var(--color-warn)]"}`}>
          {ready ? "SISTEMAS OPERACIONAIS" : "SISTEMAS PARCIAIS"}
        </span>
      </div>
    </div>
  );
}
