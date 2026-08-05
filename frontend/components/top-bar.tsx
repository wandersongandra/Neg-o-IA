"use client";

import {
  Bell,
  Command,
  Cpu,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";
import type { DashboardData } from "@/lib/types";

interface TopBarProps {
  data: DashboardData | null;
  onOpenPalette: () => void;
}

function modelLabel(): string {
  return "GPT-OSS-120B";
}

export default function TopBar({ data, onOpenPalette }: TopBarProps) {
  const online = data?.healthz?.status === "alive";
  const latency = data?.latency_ms ?? null;
  const level =
    data?.security?.authorization_level ?? data?.root?.environment ?? "online";

  return (
    <header className="glass sticky top-0 z-40 flex h-16 items-center gap-4 px-5">
      <div className="flex items-center gap-3">
        <div className="relative flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#00D4FF] shadow-[0_0_24px_-6px_rgba(0,212,255,0.7)]">
          <Cpu className="size-5 text-[#05070B]" strokeWidth={2.2} />
          <span className="absolute -right-0.5 -top-0.5 size-2 rounded-full bg-[#22C55E] ring-2 ring-[#05070B]" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-wide text-[#F8FAFC]">
            NEGÃO <span className="text-gradient glow-text">AI</span>
          </p>
          <p className="font-mono-data text-[10px] text-[#94A3B8]">
            CENTRO DE COMANDO
          </p>
        </div>
      </div>

      <button
        onClick={onOpenPalette}
        className="glass glass-hover group flex h-10 flex-1 max-w-xl items-center gap-3 rounded-xl px-4 text-left"
      >
        <Search className="size-4 text-[#94A3B8] transition-colors group-hover:text-[#00D4FF]" />
        <span className="flex-1 truncate text-sm text-[#94A3B8]">
          Pesquisar ou dar um comando ao NEGÃO…
        </span>
        <span className="glass flex items-center gap-1 rounded-md px-2 py-0.5 font-mono-data text-[10px] text-[#94A3B8]">
          <Command className="size-3" /> K
        </span>
      </button>

      <div className="ml-auto flex items-center gap-2">
        <div className="glass hidden items-center gap-2 rounded-xl px-3 py-1.5 lg:flex">
          <Sparkles className="size-3.5 text-[#00D4FF]" />
          <span className="text-xs text-[#F8FAFC]">{modelLabel()}</span>
        </div>

        <div className="glass hidden items-center gap-2 rounded-xl px-3 py-1.5 xl:flex">
          <span className="font-mono-data text-xs text-[#94A3B8]">
            {latency === null ? "--" : `${latency}ms`}
          </span>
          <span
            className={`size-1.5 rounded-full ${
              online ? "bg-[#22C55E]" : "bg-[#EF4444]"
            }`}
            style={{ boxShadow: "0 0 8px currentColor" }}
          />
          <span className="text-xs text-[#94A3B8]">resposta</span>
        </div>

        <div className="glass hidden items-center gap-2 rounded-xl px-3 py-1.5 lg:flex">
          <span
            className={`size-1.5 rounded-full ${
              online ? "bg-[#22C55E]" : "bg-[#EF4444]"
            }`}
            style={{ boxShadow: "0 0 8px currentColor" }}
          />
          <span className="text-xs text-[#94A3B8]">
            {online ? "online" : "offline"}
          </span>
        </div>

        <button
          className="glass glass-hover relative flex size-10 items-center justify-center rounded-xl text-[#94A3B8]"
          aria-label="Notificações"
        >
          <Bell className="size-4" />
          <span className="absolute right-2 top-2 size-1.5 rounded-full bg-[#F59E0B] shadow-[0_0_8px_#F59E0B]" />
        </button>
        <button
          className="glass glass-hover flex size-10 items-center justify-center rounded-xl text-[#94A3B8]"
          aria-label="Configurações"
        >
          <Settings className="size-4" />
        </button>

        <div className="flex items-center gap-2 pl-1">
          <div className="flex size-9 items-center justify-center rounded-full bg-gradient-to-br from-[#3B82F6]/40 to-[#00D4FF]/40 text-xs font-semibold text-[#F8FAFC] ring-1 ring-white/10">
            W
          </div>
          <div className="hidden leading-tight lg:block">
            <p className="text-xs font-medium text-[#F8FAFC]">Wanderson</p>
            <p className="font-mono-data text-[10px] uppercase text-[#00D4FF]">
              {level}
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}
