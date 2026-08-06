"use client";

import { useEffect, useState, type CSSProperties } from "react";
import {
  Activity,
  ArrowUp,
  BookOpen,
  Boxes,
  CheckCircle2,
  Database,
  FilePlus2,
  FolderGit2,
  GitBranch,
  HardDrive,
  Lightbulb,
  ListTodo,
  RefreshCw,
  Rocket,
  Sparkles,
  TrendingUp,
  Wrench,
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

interface TimelineEntry {
  title: string;
  tag: string;
  icon: LucideIcon;
  when: string;
  tone?: string;
}

const TIMELINE: TimelineEntry[] = [
  { title: "Projeto SGS atualizado", tag: "PROJETOS", icon: FolderGit2, when: "há 2 min" },
  { title: "Docker reiniciado", tag: "INFRA", icon: Boxes, when: "há 12 min" },
  { title: "Novo documento aprendido", tag: "MEMÓRIA", icon: FilePlus2, when: "há 26 min" },
  { title: "Banco sincronizado", tag: "DADOS", icon: Database, when: "há 41 min" },
  { title: "Backup concluído", tag: "INFRA", icon: HardDrive, when: "há 1 h" },
  { title: "Novo conhecimento criado", tag: "APRENDIZADO", icon: Lightbulb, when: "há 2 h" },
];

export function TimelinePanel() {
  return (
    <div className="glass glass-hover animate-fade-up rounded-2xl p-4">
      <SectionTitle icon={Activity} title="Linha do Tempo" subtitle="ATIVIDADES RECENTES" />
      <div className="space-y-1">
        {TIMELINE.map((entry) => (
          <div
            key={entry.title}
            className="group flex items-center gap-3 rounded-xl px-2 py-2 transition-colors hover:bg-white/[0.03]"
          >
            <div className="relative flex size-8 shrink-0 items-center justify-center rounded-lg bg-[var(--color-prime)]/10 ring-1 ring-[var(--color-prime)]/20">
              <entry.icon className="size-3.5 text-[var(--accent)]" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px] text-[var(--text-primary)]">{entry.title}</p>
              <p className="font-mono-data text-[9px] tracking-wider text-[var(--text-secondary)]">
                {entry.tag}
              </p>
            </div>
            <span className="font-mono-data shrink-0 text-[10px] text-[var(--text-secondary)]">
              {entry.when}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface Task {
  title: string;
  priority: "alta" | "média" | "baixa";
  icon: LucideIcon;
}

const TASKS: Task[] = [
  { title: "Revisar arquitetura do projeto SGS", priority: "alta", icon: FolderGit2 },
  { title: "Configurar backup da VPS", priority: "alta", icon: HardDrive },
  { title: "Atualizar documentação da API", priority: "média", icon: BookOpen },
  { title: "Testar pipeline Docker de produção", priority: "média", icon: Activity },
  { title: "Organizar knowledge vault", priority: "baixa", icon: Lightbulb },
];

const PRIORITY_STYLE: Record<Task["priority"], { label: string; cls: string; dot: string }> = {
  alta: { label: "ALTA", cls: "text-[var(--color-danger)] bg-[var(--color-danger)]/10 ring-[var(--color-danger)]/30", dot: "bg-[var(--color-danger)]" },
  média: { label: "MÉDIA", cls: "text-[var(--color-warn)] bg-[var(--color-warn)]/10 ring-[var(--color-warn)]/30", dot: "bg-[var(--color-warn)]" },
  baixa: { label: "BAIXA", cls: "text-[var(--color-ok)] bg-[var(--color-ok)]/10 ring-[var(--color-ok)]/30", dot: "bg-[var(--color-ok)]" },
};

export function TasksPanel() {
  const [done, setDone] = useState<Set<number>>(new Set());

  return (
    <div className="glass glass-hover animate-fade-up rounded-2xl p-4">
      <SectionTitle icon={ListTodo} title="Próximas Tarefas" subtitle="3 IMPORTANTES" />
      <div className="space-y-1">
        {TASKS.map((task, i) => {
          const style = PRIORITY_STYLE[task.priority];
          const isDone = done.has(i);
          return (
            <button
              key={task.title}
              onClick={() => {
                const next = new Set(done);
                if (isDone) next.delete(i);
                else next.add(i);
                setDone(next);
              }}
              className={`group flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition-all ${
                isDone ? "opacity-45" : "hover:bg-white/[0.03]"
              }`}
            >
              <task.icon
                className={`size-3.5 shrink-0 ${isDone ? "text-[var(--color-ok)]" : "text-[var(--text-secondary)] group-hover:text-[var(--accent)]"}`}
              />
              <span
                className={`min-w-0 flex-1 truncate text-[12px] ${
                  isDone ? "line-through text-[var(--text-secondary)]" : "text-[var(--text-primary)]"
                }`}
              >
                {task.title}
              </span>
              <span className={`flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 font-mono-data text-[9px] ring-1 ${style.cls}`}>
                <span className={`size-1 rounded-full ${style.dot}`} />
                {style.label}
              </span>
              <CheckCircle2
                className={`size-4 shrink-0 transition-colors ${
                  isDone ? "text-[var(--color-ok)]" : "text-[var(--text-secondary)] group-hover:text-[var(--color-ok)]"
                }`}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}

const DONUT: { label: string; value: number; color: string }[] = [
  { label: "Projetos", value: 28, color: "#3B82F6" },
  { label: "Conversas", value: 24, color: "#00D4FF" },
  { label: "Conhecimento", value: 19, color: "#4DA6FF" },
  { label: "Documentos", value: 14, color: "#22C55E" },
  { label: "Aprendizados", value: 9, color: "#93C5FD" },
  { label: "Outros", value: 6, color: "#475569" },
];

export function MemoryDonut() {
  const C = 2 * Math.PI * 56;
  let offset = 0;

  return (
    <div className="glass glass-hover animate-fade-up rounded-2xl p-4">
      <SectionTitle icon={TrendingUp} title="Uso da Memória" subtitle="DISTRIBUIÇÃO" />
      <div className="flex items-center gap-4">
        <div className="relative shrink-0">
          <svg width="150" height="150" viewBox="0 0 150 150" className="-rotate-90" aria-label="Distribuição da memória">
            <circle cx="75" cy="75" r="56" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="14" />
            {DONUT.map((seg) => {
              const len = (seg.value / 100) * C;
              const el = (
                <circle
                  key={seg.label}
                  cx="75"
                  cy="75"
                  r="56"
                  fill="none"
                  stroke={seg.color}
                  strokeWidth="14"
                  strokeLinecap="round"
                  strokeDasharray={`${len} ${C - len}`}
                  strokeDashoffset={-offset}
                  className="animate-draw-ring"
                  style={{
                    "--ring-offset": `${-offset}`,
                    animationDelay: `${offset / C}s`,
                    transition: "stroke-dasharray 700ms ease",
                    filter: `drop-shadow(0 0 6px ${seg.color}66)`,
                  } as CSSProperties}
                />
              );
              offset += len;
              return el;
            })}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <p className="font-mono-data text-xl font-bold text-[var(--text-primary)]">46%</p>
            <p className="font-mono-data text-[8px] tracking-[0.25em] text-[var(--text-secondary)]">
              EM USO
            </p>
          </div>
        </div>
        <div className="flex-1 space-y-2">
          {DONUT.map((seg) => (
            <div key={seg.label} className="flex items-center gap-2">
              <span
                className="size-2 rounded-sm"
                style={{ background: seg.color, boxShadow: `0 0 8px ${seg.color}88` }}
              />
              <span className="flex-1 text-[11px] text-[var(--text-secondary)]">{seg.label}</span>
              <span className="font-mono-data text-[11px] font-semibold text-[var(--text-primary)]">
                {seg.value}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface GraphNode {
  label: string;
  x: number;
  y: number;
  size?: number;
}

const GRAPH_CENTER = { label: "NEGÃO", x: 350, y: 200 };
const GRAPH_NODES: GraphNode[] = [
  { label: "SGS", x: 180, y: 78 },
  { label: "Gandra Tecnologia", x: 350, y: 58 },
  { label: "Docker", x: 522, y: 90 },
  { label: "Python", x: 604, y: 200 },
  { label: "Clientes", x: 520, y: 312 },
  { label: "Projetos", x: 350, y: 348 },
  { label: "Infraestrutura", x: 180, y: 322 },
  { label: "Banco de Dados", x: 96, y: 200 },
  { label: "Documentos", x: 208, y: 128 },
  { label: "Cloudflare", x: 498, y: 140 },
];

export function KnowledgeGraph() {
  return (
    <div className="glass glass-hover animate-fade-up rounded-2xl p-4">
      <SectionTitle icon={GitBranch} title="Knowledge Graph" subtitle="REDE DE CONHECIMENTO" />
      <svg viewBox="0 0 700 420" className="w-full" aria-label="Grafo de conhecimento do NEGÃO">
        <defs>
          <linearGradient id="knowledge-flow" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.1" />
            <stop offset="45%" stopColor="var(--accent-glow)" stopOpacity="0.9" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.12" />
          </linearGradient>
          <filter id="node-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        {GRAPH_NODES.map((node) => (
          <g key={node.label} className="animate-float" style={{ animationDelay: `${(node.x + node.y) % 9 * -0.45}s`, animationDuration: `${5 + (node.y % 4)}s` }}>
            <line
              x1={GRAPH_CENTER.x}
              y1={GRAPH_CENTER.y}
              x2={node.x}
              y2={node.y}
              stroke="url(#knowledge-flow)"
              strokeWidth="1.4"
              strokeDasharray="12 10"
              className="animate-data-flow"
            />
            <circle
              cx={node.x}
              cy={node.y}
              r={node.size ?? 9}
              fill="var(--bg-secondary)"
              stroke="rgba(0,212,255,0.5)"
              strokeWidth="1"
              className="transition-all duration-300"
              style={{ filter: "url(#node-glow)" }}
            />
            <text
              x={node.x}
              y={node.y + (node.size ?? 9) + 14}
              textAnchor="middle"
              className="fill-[var(--text-secondary)]"
              style={{ fontSize: 11, fontFamily: "var(--font-jetbrains), monospace" }}
            >
              {node.label}
            </text>
          </g>
        ))}

        <circle
          cx={GRAPH_CENTER.x}
          cy={GRAPH_CENTER.y}
          r="52"
          fill="rgba(59,130,246,0.12)"
          stroke="rgba(0,212,255,0.45)"
          strokeWidth="1.5"
          className="animate-glow-pulse"
          style={{ filter: "drop-shadow(0 0 14px rgba(0,212,255,0.5))" }}
        />
        <circle cx={GRAPH_CENTER.x} cy={GRAPH_CENTER.y} r="40" fill="rgba(59,130,246,0.2)" stroke="rgba(0,212,255,0.3)" strokeWidth="1" />
        <text
          x={GRAPH_CENTER.x}
          y={GRAPH_CENTER.y - 4}
          textAnchor="middle"
          className="fill-[var(--text-primary)] font-bold"
          style={{ fontSize: 15, fontFamily: "var(--font-jetbrains), monospace", filter: "drop-shadow(0 0 8px rgba(0,212,255,0.8))" }}
        >
          NEGÃO
        </text>
        <text
          x={GRAPH_CENTER.x}
          y={GRAPH_CENTER.y + 16}
          textAnchor="middle"
          className="fill-[var(--accent)]"
          style={{ fontSize: 8, letterSpacing: 3, fontFamily: "var(--font-jetbrains), monospace" }}
        >
          CORE
        </text>
      </svg>
    </div>
  );
}

const LEARNINGS = [
  { title: "Nova arquitetura FastAPI", icon: Rocket },
  { title: "Melhor prática Docker", icon: Boxes },
  { title: "Novo padrão PostgreSQL", icon: Database },
  { title: "Segurança OWASP", icon: Wrench },
  { title: "Monitoramento VPS", icon: Activity },
];

export function LearningsPanel() {
  return (
    <div className="glass glass-hover animate-fade-up rounded-2xl p-4">
      <SectionTitle icon={Sparkles} title="Aprendizados Recentes" subtitle="HOJE +12" />
      <div className="space-y-1">
        {LEARNINGS.map((item) => (
          <div
            key={item.title}
            className="flex items-center gap-3 rounded-xl px-2 py-2 transition-colors hover:bg-white/[0.03]"
          >
            <span className="flex size-7 items-center justify-center rounded-lg bg-[var(--color-ok)]/10 ring-1 ring-[var(--color-ok)]/25">
              <item.icon className="size-3.5 text-[var(--color-ok)]" />
            </span>
            <span className="text-[12px] text-[var(--text-primary)]">{item.title}</span>
            <ArrowUp className="ml-auto size-3 text-[var(--color-ok)]" />
          </div>
        ))}
      </div>
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
  const lastSync = data
    ? (() => {
        const d = new Date(data.fetched_at);
        return Number.isNaN(d.getTime())
          ? "--"
          : d.toLocaleTimeString("pt-BR", { hour12: false });
      })()
    : "--";

  const cells: { label: string; value: string }[] = [
    { label: "SERVIDOR", value: "VPS-01 · negao" },
    { label: "IP", value: "10.0.0.7" },
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
