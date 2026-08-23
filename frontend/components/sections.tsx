"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  GitBranch,
  ListTodo,
  RefreshCw,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { DashboardData } from "@/lib/types";

function SectionTitle({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Icon className="size-4 text-[var(--accent)]" />
      <div className="leading-tight">
        <h3 className="text-[13px] font-semibold text-[var(--text-primary)]">{title}</h3>
        {subtitle ? (
          <p className="font-mono-data text-[9px] tracking-[0.2em] text-[var(--text-secondary)]">
            {subtitle}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export function TimelinePanel({ data }: { data: DashboardData | null }) {
  const logs = data?.logs?.slice(-6).reverse() ?? [];

  return (
    <div className="glass glass-hover animate-fade-up rounded-2xl p-4">
      <SectionTitle icon={Activity} title="Linha do Tempo" subtitle="ATIVIDADES RECENTES" />
      <div className="space-y-1">
        {logs.length === 0 ? (
          <p className="px-2 py-4 text-xs text-[var(--text-secondary)]">Sem eventos recentes sincronizados.</p>
        ) : logs.map((log, index) => (
          <div key={`${log}-${index}`} className="group flex items-center gap-3 rounded-xl px-2 py-2 transition-colors hover:bg-white/[0.03]">
            <div className="relative flex size-8 shrink-0 items-center justify-center rounded-lg bg-[var(--color-prime)]/10 ring-1 ring-[var(--color-prime)]/20">
              <Activity className="size-3.5 text-[var(--accent)]" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px] text-[var(--text-primary)]">{log}</p>
              <p className="font-mono-data text-[9px] tracking-wider text-[var(--text-secondary)]">LOG DO BACKEND</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function TasksPanel() {
  return (
    <div className="glass glass-hover animate-fade-up rounded-2xl p-4">
      <SectionTitle icon={ListTodo} title="Próximas Tarefas" subtitle="AGUARDANDO SINCRONIZAÇÃO" />
      <p className="px-2 py-4 text-xs text-[var(--text-secondary)]">Nenhuma tarefa foi carregada de uma fonte conectada.</p>
    </div>
  );
}

export function MemoryDonut() {
  return (
    <div className="glass glass-hover animate-fade-up rounded-2xl p-4">
      <SectionTitle icon={TrendingUp} title="Uso da Memória" subtitle="DISTRIBUIÇÃO" />
      <div className="flex min-h-36 items-center justify-center rounded-xl border border-dashed border-[var(--border)] px-4 text-center">
        <p className="max-w-xs text-xs text-[var(--text-secondary)]">A distribuição só será exibida quando a fonte de memória estiver conectada.</p>
      </div>
    </div>
  );
}

export function KnowledgeGraph() {
  return (
    <div className="glass glass-hover animate-fade-up rounded-2xl p-4">
      <SectionTitle icon={GitBranch} title="Knowledge Graph" subtitle="REDE DE CONHECIMENTO" />
      <div className="flex min-h-48 items-center justify-center rounded-xl border border-dashed border-[var(--border)] px-4 text-center">
        <p className="max-w-sm text-xs text-[var(--text-secondary)]">O grafo aparecerá quando houver entidades e relacionamentos carregados.</p>
      </div>
    </div>
  );
}

export function LearningsPanel() {
  return (
    <div className="glass glass-hover animate-fade-up rounded-2xl p-4">
      <SectionTitle icon={Sparkles} title="Aprendizados Recentes" subtitle="SEM DADOS" />
      <p className="px-2 py-4 text-xs text-[var(--text-secondary)]">Nenhum aprendizado foi sincronizado ainda.</p>
    </div>
  );
}

export function FooterBar({ data }: { data: DashboardData | null }) {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const env = data?.root?.environment ?? "--";
  const version = data?.root?.version ?? "--";
  const server = data?.root?.name ?? "--";
  const lastSync = data
    ? (() => {
        const d = new Date(data.fetched_at);
        return Number.isNaN(d.getTime())
          ? "--"
          : d.toLocaleTimeString("pt-BR", { hour12: false });
      })()
    : "--";

  const cells: { label: string; value: string }[] = [
    { label: "SERVIDOR", value: server },
    { label: "VERSÃO", value: `v${version}` },
    {
      label: "AMBIENTE",
      value: env === "production" ? "PRODUÇÃO" : env.toUpperCase() || "DEV",
    },
    { label: "ÚLTIMA SINCRONIZAÇÃO", value: lastSync },
    {
      label: "HORA",
      value: now.toLocaleTimeString("pt-BR", { hour12: false }),
    },
    {
      label: "DATA",
      value: now.toLocaleDateString("pt-BR"),
    },
  ];

  return (
    <footer className="glass animate-fade-up rounded-2xl px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-x-8 gap-y-2">
        {cells.map((cell) => (
          <div key={cell.label} className="leading-tight">
            <p className="font-mono-data text-[8px] tracking-[0.25em] text-[var(--text-secondary)]">
              {cell.label}
            </p>
            <p className="font-mono-data text-[11px] font-semibold text-[var(--text-primary)]">
              {cell.value}
            </p>
          </div>
        ))}
        <div className="flex items-center gap-1.5 text-[var(--color-ok)]">
          <RefreshCw className="size-3 animate-spin-slow" />
          <span className="font-mono-data text-[10px]">
            {data?.backend_reachable ? "SINCRONIZADO" : "SEM CONEXÃO"}
          </span>
        </div>
      </div>
    </footer>
  );
}
