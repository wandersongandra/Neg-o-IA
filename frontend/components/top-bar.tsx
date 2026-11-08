"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Command,
  Cpu,
  Search,
  Settings,
  BrainCircuit,
} from "lucide-react";
import type { BrainRouterInfo, DashboardData } from "@/lib/types";
import { InstallPrompt, InstallButton } from "@/components/pwa/install-prompt";
import { PushNotifications } from "@/components/pwa/push-notifications";

interface TopBarProps {
  data: DashboardData | null;
  onOpenPalette?: () => void;
  commandLabel?: string;
}

function useBrainModel(): string | null {
  const [model, setModel] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    fetch("/api/proxy/brain/router", { cache: "no-store", signal: controller.signal })
      .then((res) =>
        res.ok ? (res.json() as Promise<BrainRouterInfo>) : Promise.resolve(null),
      )
      .then((data) => {
        if (!cancelled && data?.primary_model) setModel(data.primary_model);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);
  return model;
}


export default function TopBar({ data, onOpenPalette, commandLabel }: TopBarProps) {
  const router = useRouter();
  const model = useBrainModel();
  const online = data?.healthz?.status === "alive" || data?.healthz?.status === "ok";
  const latency = data?.latency_ms ?? null;
  const level = data?.security?.authorization_level ?? "offline";
  return (
    <header
      className="sticky top-0 z-40 flex h-[4.5rem] items-center gap-3 overflow-visible border-b border-[var(--border)] bg-[var(--bg-primary)]/95 px-4 pt-[env(safe-area-inset-top)] sm:px-6 sm:gap-5"
    >
      <div className="flex items-center gap-3">
        <div className="relative flex size-9 items-center justify-center rounded-lg bg-[var(--accent)] text-[#1b1512]">
          <Cpu className="size-5" strokeWidth={2.2} />
        </div>
        <div className="hidden leading-tight min-[400px]:block">
          <p className="text-[.78rem] font-bold tracking-[.18em] text-[var(--text-primary)]">
            ULTRON
          </p>
          <p className="mt-1 text-[.65rem] tracking-[.08em] text-[var(--text-secondary)]">
            CENTRO DE COMANDO
          </p>
        </div>
      </div>

      <button
        onClick={() => onOpenPalette?.()}
        type="button"
        disabled={!onOpenPalette}
        aria-label={commandLabel ?? "Abrir paleta de comandos"}
        className="interactive-control group flex h-10 min-w-0 flex-1 max-w-xl items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-4 text-left disabled:cursor-default disabled:opacity-60 disabled:hover:transform-none"
      >
        <Search className="size-4 shrink-0 text-[var(--text-secondary)] transition-colors group-hover:text-[var(--accent)]" />
        <span className="flex-1 truncate text-sm text-[var(--text-secondary)]">
          {commandLabel ?? "Pesquisar ou dar um comando à Ultron…"}
        </span>
        {!commandLabel && onOpenPalette ? (
          <span className="hidden items-center gap-1 rounded-md border border-[var(--border)] px-2 py-0.5 font-mono-data text-[10px] text-[var(--text-secondary)] sm:flex">
            <Command className="size-3" /> K
          </span>
        ) : null}
      </button>

      <div className="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
        <div className="hidden items-center gap-2 border-l border-[var(--border)] pl-4 lg:flex">
          <BrainCircuit className="size-3.5 text-[var(--accent)]" />
          <span className="max-w-[160px] truncate text-xs text-[var(--text-primary)]">{model ?? "—"}</span>
        </div>

        <div className="hidden items-center gap-2 border-l border-[var(--border)] pl-4 xl:flex">
          <span className="font-mono-data text-xs text-[var(--text-secondary)]">
            {latency === null ? "--" : `${latency}ms`}
          </span>
          <span
            className={`size-1.5 rounded-full ${
              online ? "bg-[var(--color-ok)]" : "bg-[var(--color-danger)]"
            }`}
          />
          <span className="text-xs text-[var(--text-secondary)]">resposta</span>
        </div>

        <div className="hidden items-center gap-2 border-l border-[var(--border)] pl-4 lg:flex">
          <span
            className={`size-1.5 rounded-full ${
              online ? "bg-[var(--color-ok)]" : "bg-[var(--color-danger)]"
            }`}
          />
          <span className="text-xs text-[var(--text-secondary)]">
            {online ? "online" : "offline"}
          </span>
        </div>



        <PushNotifications />

        <InstallButton />

        <button
          className="interactive-control flex size-9 items-center justify-center rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] sm:size-10"
          aria-label="Configurações"
          type="button"
          onClick={() => router.push("/config")}
        >
          <Settings className="size-4" />
        </button>

        <div className="hidden items-center gap-2 pl-1 sm:flex">
          <div className="flex size-9 items-center justify-center rounded-lg bg-[var(--accent)] text-xs font-semibold text-[#1b1512]">
            W
          </div>
          <div className="hidden leading-tight lg:block">
            <p className="text-xs font-medium text-[var(--text-primary)]">Wanderson</p>
            <p className="font-mono-data text-[10px] uppercase text-[var(--accent)]">
              {level}
            </p>
          </div>
        </div>
      </div>
      <InstallPrompt />
    </header>
  );
}
