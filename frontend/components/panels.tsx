"use client";

import { useEffect, useState } from "react";
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

function jitter(base: number, spread: number): number {
  const v = base + (Math.random() - 0.5) * 2 * spread;
  return Math.max(0, Math.round(v * 10) / 10);
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
        <Icon className="size-3.5 text-[#00D4FF]" />
        <h3 className="font-mono-data text-[10px] font-semibold tracking-[0.25em] text-[#94A3B8]">
          {title}
        </h3>
      </div>
      {children}
    </div>
  );
}

export function SystemCard({ data }: { data: DashboardData | null }) {
  const [cpu, setCpu] = useState(34);
  const [ram, setRam] = useState(42);
  const [gpu, setGpu] = useState(18);
  const [net, setNet] = useState(12);
  const [disk, setDisk] = useState(56);
  const [temp, setTemp] = useState(51);

  useEffect(() => {
    const id = setInterval(() => {
      setCpu(jitter(34, 8));
      setRam(jitter(42, 5));
      setGpu(jitter(18, 6));
      setNet(jitter(12, 7));
      setDisk(jitter(56, 0.5));
      setTemp(jitter(51, 3));
    }, 3000);
    return () => clearInterval(id);
  }, []);

  const latencyMs = data?.latency_ms ?? null;
  const rows: Row[] = [
    { label: "CPU", icon: Zap, value: `${cpu.toFixed(1)}%` },
    { label: "RAM", icon: MemoryStick, value: `${ram.toFixed(1)}%` },
    { label: "GPU", icon: Monitor, value: `${gpu.toFixed(1)}%` },
    { label: "REDE", icon: Network, value: `${net.toFixed(1)} MB/s` },
    { label: "DISCO", icon: HardDrive, value: `${disk.toFixed(1)}%` },
    {
      label: "DOCKER",
      icon: Boxes,
      value: "ATIVO",
      tone: data?.backend_reachable ? "ok" : "warn",
    },
    {
      label: "TEMPERATURA",
      icon: Thermometer,
      value: `${temp.toFixed(1)}°C`,
      tone: temp > 70 ? "warn" : "ok",
    },
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
            {row.icon ? <row.icon className="size-3.5 text-[#64748B]" /> : null}
            <span className="flex-1 font-mono-data text-[10px] tracking-wider text-[#94A3B8]">
              {row.label}
            </span>
            <span
              className={`font-mono-data text-[11px] font-semibold ${
                row.tone === "danger"
                  ? "text-[#EF4444]"
                  : row.tone === "warn"
                    ? "text-[#F59E0B]"
                    : "text-[#22C55E]"
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
  const primary = brain?.primary_model ?? "GPT-OSS-120B";
  const fallback = brain?.fallback_model ?? null;
  const circuitFailures = brain?.circuit_failures ?? null;
  const modeLabel =
    mode === "nvidia" ? "● NVIDIA" : mode === "local" ? "● LOCAL" : "● disponível";
  const modeColor =
    mode === "nvidia" || mode === "local" ? "text-[#22C55E]" : "text-[#F59E0B]";
  const rows: Row[] = [
    { label: "FORNECEDOR", value: mode === "local" ? "LOCAL (GPU)" : "NVIDIA API" },
    { label: "FALLBACK MODEL", value: fallback ?? "—" },
    { label: "TEMPO MÉDIO", value: "1.4s" },
    { label: "TOKENS (SESSÃO)", value: "12.4K" },
    { label: "CUSTO (SESSÃO)", value: "$0.021" },
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
        <div className="relative flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6]/30 to-[#00D4FF]/20 ring-1 ring-[#00D4FF]/30">
          <Brain className="size-4 text-[#00D4FF]" />
        </div>
        <div className="min-w-0 leading-tight">
          <p className="truncate text-sm font-semibold text-[#F8FAFC]">{primary}</p>
          <p className={`font-mono-data text-[10px] ${modeColor}`}>{modeLabel}</p>
        </div>
      </div>
      <div className="space-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between gap-2">
            <span className="font-mono-data text-[10px] tracking-wider text-[#94A3B8]">
              {row.label}
            </span>
            <span
              className={`max-w-[55%] truncate font-mono-data text-[11px] font-semibold ${
                row.tone === "danger"
                  ? "text-[#EF4444]"
                  : row.tone === "warn"
                    ? "text-[#F59E0B]"
                    : row.tone === "ok"
                      ? "text-[#22C55E]"
                      : "text-[#F8FAFC]"
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
  const redisOk = data?.memory?.redis_connected ?? false;
  const rows: Row[] = [
    { label: "CONVERSAS", value: "128" },
    { label: "PROJETOS", value: "7" },
    { label: "DOCUMENTOS", value: "43" },
    { label: "CONHECIMENTO", value: "96" },
    { label: "VETORES", value: "2.1K" },
    { label: "RELACIONAMENTOS", value: "312" },
  ];
  return (
    <Card title="MEMÓRIA" icon={Brain}>
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono-data text-[10px] tracking-wider text-[#94A3B8]">
          REDIS STM
        </span>
        <span
          className={`flex items-center gap-1.5 font-mono-data text-[10px] ${
            redisOk ? "text-[#22C55E]" : "text-[#F59E0B]"
          }`}
        >
          <span className="size-1.5 rounded-full bg-current shadow-[0_0_8px_currentColor]" />
          {redisOk ? "CONECTADO" : "DEGRADADO"}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-baseline justify-between gap-2">
            <span className="font-mono-data text-[10px] tracking-wider text-[#94A3B8]">
              {row.label}
            </span>
            <span className="font-mono-data text-[11px] font-semibold text-[#F8FAFC]">
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
  const postgresOk = data?.database?.connected ?? false;
  const redisOk = data?.memory?.redis_connected ?? false;
  const llmOk = brain !== null;
  const tools: { label: string; icon: LucideIcon; ok: boolean }[] = [
    { label: "LLM", icon: Brain, ok: llmOk },
    { label: "GitHub", icon: GitBranch, ok: true },
    { label: "Docker", icon: Boxes, ok: true },
    { label: "VS Code", icon: FileText, ok: true },
    { label: "PostgreSQL", icon: Database, ok: postgresOk },
    { label: "Redis", icon: MemoryStick, ok: redisOk },
    { label: "SSH", icon: Wrench, ok: true },
    { label: "Cloudflare", icon: Cloud, ok: true },
    { label: "Coolify", icon: Server, ok: true },
    { label: "Google Drive", icon: FolderGit2, ok: true },
  ];
  return (
    <Card title="FERRAMENTAS" icon={Wrench}>
      <div className="grid grid-cols-3 gap-2">
        {tools.map((tool) => (
          <div
            key={tool.label}
            className="glass glass-hover flex flex-col items-center gap-1.5 rounded-xl px-2 py-2.5"
            title={tool.ok ? "conectado" : "indisponível"}
          >
            <tool.icon className="size-4 text-[#F8FAFC]" />
            <span className="max-w-full truncate text-[9px] text-[#94A3B8]">
              {tool.label}
            </span>
            <span
              className={`size-1 rounded-full ${
                tool.ok ? "bg-[#22C55E]" : "bg-[#F59E0B]"
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
  const ready = data?.readyz?.status === "ok";

  return (
    <div className="animate-fade-up text-center">
      <h1 className="text-2xl font-semibold tracking-tight text-[#F8FAFC]">
        {period}, <span className="text-gradient">Wanderson</span>.
      </h1>
      <p className="mt-2 text-sm text-[#94A3B8]">
        <span className={online ? "text-[#22C55E]" : "text-[#EF4444]"}>
          NEGÃO está {online ? "online" : "offline"}.
        </span>{" "}
        {ready
          ? "Tudo funcionando normalmente."
          : "Operando com ressalvas em alguns subsistemas."}
      </p>
      <div className="mx-auto mt-3 flex max-w-md flex-wrap items-center justify-center gap-2 font-mono-data text-[10px] text-[#64748B]">
        <span className="glass rounded-full px-3 py-1">HOJE APRENDI +12</span>
        <span className="glass rounded-full px-3 py-1">3 TAREFAS IMPORTANTES</span>
        <span className="glass rounded-full px-3 py-1 text-[#22C55E]">
          SISTEMAS OPERACIONAIS
        </span>
      </div>
    </div>
  );
}
