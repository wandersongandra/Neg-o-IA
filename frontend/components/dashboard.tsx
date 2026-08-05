"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  Brain,
  Database,
  GitBranch,
  MessageSquareText,
  Mic,
  Play,
  Search,
  Wrench,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { BrainStatus, ConversationStatus, DashboardData } from "@/lib/types";
import TopBar from "@/components/top-bar";
import Sidebar from "@/components/sidebar";
import CoreSphere from "@/components/core-sphere";
import {
  Greeting,
  MemoryCard,
  ModelCard,
  SystemCard,
  ToolsCard,
} from "@/components/panels";
import {
  FooterBar,
  KnowledgeGraph,
  LearningsPanel,
  MemoryDonut,
  TasksPanel,
  TimelinePanel,
} from "@/components/sections";

const POLL_MS = 5000;

interface Command {
  label: string;
  icon: LucideIcon;
  href?: string;
}

const COMMANDS: Command[] = [
  { label: "Abrir conversa com o NEGÃO", icon: MessageSquareText, href: "/conversa" },
  { label: "Voz", icon: Mic, href: "/voz" },
  { label: "Monitor", icon: Activity, href: "/monitor" },
  { label: "Consultar memória", icon: Brain },
  { label: "Buscar conhecimento", icon: GitBranch },
  { label: "Acessar banco de dados", icon: Database },
  { label: "Gerenciar ferramentas", icon: Wrench },
  { label: "Iniciar automação", icon: Play },
];

export default function Dashboard() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [brain, setBrain] = useState<BrainStatus | null>(null);
  const [, setConv] = useState<ConversationStatus | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [filter, setFilter] = useState("");

  const load = useCallback(async () => {
    const [dashRes, brainRes, convRes] = await Promise.all([
      fetch("/api/dashboard", { cache: "no-store" }).catch(() => null),
      fetch("/api/proxy/brain/status", { cache: "no-store" }).catch(() => null),
      fetch("/api/proxy/conversation/status", { cache: "no-store" }).catch(() => null),
    ]);
    if (dashRes?.ok) {
      try {
        setData((await dashRes.json()) as DashboardData);
      } catch {
        setData(null);
      }
    } else {
      setData(null);
    }
    if (brainRes?.ok) {
      try {
        setBrain((await brainRes.json()) as BrainStatus);
      } catch {
        setBrain(null);
      }
    } else {
      setBrain(null);
    }
    if (convRes?.ok) {
      try {
        setConv((await convRes.json()) as ConversationStatus);
      } catch {
        setConv(null);
      }
    } else {
      setConv(null);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    const uptimeStart = Date.now();
    const uptimeId = setInterval(() => {
      const el = document.getElementById("core-uptime");
      if (!el) return;
      const s = Math.floor((Date.now() - uptimeStart) / 1000);
      const hh = String(Math.floor(s / 3600)).padStart(2, "0");
      const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
      const ss = String(s % 60).padStart(2, "0");
      el.textContent = `${hh}:${mm}:${ss}`;
    }, 1000);
    return () => clearInterval(uptimeId);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((open) => !open);
      }
      if (e.key === "Escape") setPaletteOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const filtered = COMMANDS.filter((c) =>
    c.label.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar data={data} onOpenPalette={() => setPaletteOpen(true)} />

      <div className="flex flex-1">
        <Sidebar data={data} onNavigate={() => undefined} />

        <main className="flex-1 space-y-6 overflow-x-hidden p-5 md:p-6">
          <section className="grid grid-cols-12 gap-6">
            <div className="col-span-12 lg:col-span-3">
              <SystemCard data={data} />
            </div>

            <div className="col-span-12 lg:col-span-6">
              <Greeting data={data} />
              <CoreSphere data={data} brain={brain} />
            </div>

            <div className="col-span-12 space-y-4 lg:col-span-3">
              <ModelCard brain={brain} />
              <MemoryCard data={data} />
              <ToolsCard data={data} brain={brain} />
            </div>
          </section>

          <section className="grid grid-cols-12 gap-6">
            <div className="col-span-12 xl:col-span-4">
              <TimelinePanel />
            </div>
            <div className="col-span-12 xl:col-span-4">
              <TasksPanel />
            </div>
            <div className="col-span-12 xl:col-span-4">
              <MemoryDonut />
            </div>
          </section>

          <section className="grid grid-cols-12 gap-6">
            <div className="col-span-12 xl:col-span-8">
              <KnowledgeGraph />
            </div>
            <div className="col-span-12 xl:col-span-4">
              <LearningsPanel />
            </div>
          </section>

          <FooterBar data={data} />
        </main>
      </div>

      {paletteOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 p-6 backdrop-blur-sm"
          onClick={() => setPaletteOpen(false)}
        >
          <div
            className="glass w-full max-w-xl animate-fade-up rounded-2xl p-2"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-white/[0.06] px-3 py-3">
              <Search className="size-4 text-[#00D4FF]" />
              <input
                autoFocus
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Comando para o NEGÃO…"
                className="flex-1 bg-transparent text-sm text-[#F8FAFC] outline-none placeholder:text-[#64748B]"
              />
              <button
                onClick={() => setPaletteOpen(false)}
                className="text-[#64748B] transition-colors hover:text-[#F8FAFC]"
                aria-label="Fechar"
              >
                <X className="size-4" />
              </button>
            </div>
            <div className="max-h-80 overflow-y-auto py-1">
              {filtered.map((cmd) => (
                <button
                  key={cmd.label}
                  onClick={() => {
                    setPaletteOpen(false);
                    if (cmd.href) router.push(cmd.href);
                  }}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-[#E2E8F0] transition-colors hover:bg-[#3B82F6]/10 hover:text-[#F8FAFC]"
                >
                  <cmd.icon className="size-4 text-[#64748B]" />
                  {cmd.label}
                </button>
              ))}
              {filtered.length === 0 && (
                <p className="px-3 py-4 text-center text-sm text-[#64748B]">
                  Nenhum comando encontrado
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
