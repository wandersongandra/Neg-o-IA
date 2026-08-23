"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Command,
  Cpu,
  Palette,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";
import type { BrainRouterInfo, DashboardData } from "@/lib/types";
import { InstallPrompt, InstallButton } from "@/components/pwa/install-prompt";
import { PushNotifications } from "@/components/pwa/push-notifications";

interface TopBarProps {
  data: DashboardData | null;
  onOpenPalette: () => void;
}

type Theme = "azul" | "esmeralda" | "magenta";

const THEME_LABELS: Record<Theme, string> = {
  azul: "Azul",
  esmeralda: "Esmeralda",
  magenta: "Magenta",
};

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

function useTheme(): { theme: Theme; setTheme: (t: Theme) => void } {
  const [theme, setThemeState] = useState<Theme>("azul");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem("sophie-theme") as Theme | null;
    if (stored) {
      setThemeState(stored);
      document.documentElement.dataset.theme = stored;
    }
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const handleStorage = (e: StorageEvent) => {
      if (e.key === "sophie-theme" && e.newValue) {
        const newTheme = e.newValue as Theme;
        setThemeState(newTheme);
        document.documentElement.dataset.theme = newTheme;
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [mounted]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem("sophie-theme", newTheme);
    document.documentElement.dataset.theme = newTheme;
  };

  return { theme, setTheme };
}

export default function TopBar({ data, onOpenPalette }: TopBarProps) {
  const router = useRouter();
  const model = useBrainModel();
  const online = data?.healthz?.status === "alive";
  const latency = data?.latency_ms ?? null;
  const level =
    data?.security?.authorization_level ?? data?.root?.environment ?? "offline";
  const { theme, setTheme } = useTheme();
  const [themeMenuOpen, setThemeMenuOpen] = useState(false);
  const themeMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!themeMenuOpen) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (themeMenuRef.current && !themeMenuRef.current.contains(event.target as Node)) {
        setThemeMenuOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setThemeMenuOpen(false);
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [themeMenuOpen]);

  return (
    <header
      className="glass command-deck sticky top-0 z-40 flex h-16 items-center gap-3 overflow-x-hidden px-4 pt-[env(safe-area-inset-top)] sm:gap-4 sm:px-5"
      data-system-status={online ? "SYSTEM // LIVE" : "SYSTEM // OFFLINE"}
    >
      <div className="flex items-center gap-3">
        <div className="relative flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--color-prime)] to-[var(--accent)] shadow-[0_0_24px_-6px_var(--accent-glow)]">
          <Cpu className="size-5 text-[var(--bg-primary)]" strokeWidth={2.2} />
          <span className={`absolute -right-0.5 -top-0.5 size-2 rounded-full ${online ? "bg-[var(--color-ok)]" : "bg-[var(--color-danger)]"} ring-2 ring-[var(--bg-primary)]`} />
        </div>
        <div className="hidden leading-tight min-[400px]:block">
          <p className="hud-title text-sm text-[var(--text-primary)]">
            SOPHIE <span className="text-gradient glow-text">AI</span>
          </p>
          <p className="font-mono-data text-[10px] text-[var(--text-secondary)]">
            CENTRO DE COMANDO
          </p>
        </div>
      </div>

      <button
        onClick={onOpenPalette}
        type="button"
        className="glass glass-hover interactive-control group flex h-10 min-w-0 flex-1 max-w-xl items-center gap-3 rounded-xl px-4 text-left"
      >
        <Search className="size-4 shrink-0 text-[var(--text-secondary)] transition-colors group-hover:text-[var(--accent)]" />
        <span className="flex-1 truncate text-sm text-[var(--text-secondary)]">
          Pesquisar ou dar um comando à Sophie…
        </span>
        <span className="glass hidden items-center gap-1 rounded-md px-2 py-0.5 font-mono-data text-[10px] text-[var(--text-secondary)] sm:flex">
          <Command className="size-3" /> K
        </span>
      </button>

      <div className="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
        <div className="glass hidden items-center gap-2 rounded-xl px-3 py-1.5 lg:flex">
          <Sparkles className="size-3.5 text-[var(--accent)]" />
          <span className="max-w-[160px] truncate text-xs text-[var(--text-primary)]">{model ?? "—"}</span>
        </div>

        <div className="glass hidden items-center gap-2 rounded-xl px-3 py-1.5 xl:flex">
          <span className="font-mono-data text-xs text-[var(--text-secondary)]">
            {latency === null ? "--" : `${latency}ms`}
          </span>
          <span
            className={`size-1.5 rounded-full ${
              online ? "bg-[var(--color-ok)]" : "bg-[var(--color-danger)]"
            }`}
            style={{ boxShadow: "0 0 8px currentColor" }}
          />
          <span className="text-xs text-[var(--text-secondary)]">resposta</span>
        </div>

        <div className="glass hidden items-center gap-2 rounded-xl px-3 py-1.5 lg:flex">
          <span
            className={`size-1.5 rounded-full ${
              online ? "bg-[var(--color-ok)]" : "bg-[var(--color-danger)]"
            }`}
            style={{ boxShadow: "0 0 8px currentColor" }}
          />
          <span className="text-xs text-[var(--text-secondary)]">
            {online ? "online" : "offline"}
          </span>
        </div>

      <div ref={themeMenuRef} className="relative">
          <button
            className="glass glass-hover interactive-control flex size-9 items-center justify-center rounded-xl text-[var(--text-secondary)] sm:size-10"
            aria-label="Tema"
            aria-haspopup="menu"
            aria-expanded={themeMenuOpen}
            aria-controls="theme-menu"
            type="button"
            onClick={() => setThemeMenuOpen((open) => !open)}
          >
            <Palette className="size-4 transition-colors hover:text-[var(--accent)]" />
          </button>
          {themeMenuOpen ? <div id="theme-menu" role="menu" className="absolute right-0 top-full z-50 mt-2 flex min-w-[140px] flex-col rounded-xl border border-[var(--border)] glass p-1 shadow-lg">
            {(["azul", "esmeralda", "magenta"] as Theme[]).map((t) => (
              <button
                key={t}
                type="button"
                role="menuitemradio"
                aria-checked={theme === t}
                onClick={() => {
                  setTheme(t);
                  setThemeMenuOpen(false);
                }}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                  theme === t
                    ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                    : "text-[var(--text-secondary)] hover:bg-white/[0.03] hover:text-[var(--text-primary)]"
                }`}
              >
                <span
                  className="size-3 rounded-full ring-2"
                  style={{
                    background: t === "azul" ? "#00d4ff" : t === "esmeralda" ? "#10b981" : "#d946ef",
                    borderColor: t === "azul" ? "#4da6ff" : t === "esmeralda" ? "#34d399" : "#f0abfc",
                  }}
                />
                {THEME_LABELS[t]}
                {theme === t && <Palette className="size-3.5 ml-auto text-[var(--accent)]" />}
              </button>
            ))}
          </div> : null}
        </div>

        <PushNotifications />

        <InstallButton />

        <button
          className="glass glass-hover interactive-control flex size-9 items-center justify-center rounded-xl text-[var(--text-secondary)] sm:size-10"
          aria-label="Configurações"
          type="button"
          onClick={() => router.push("/config")}
        >
          <Settings className="size-4" />
        </button>

        <div className="hidden items-center gap-2 pl-1 sm:flex">
          <div className="flex size-9 items-center justify-center rounded-full bg-gradient-to-br from-[var(--color-prime)]/40 to-[var(--accent)]/40 text-xs font-semibold text-[var(--text-primary)] ring-1 ring-white/10">
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
