"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  Bot,
  Braces,
  Boxes,
  Brain,
  Cloud,
  Database,
  Eye,
  FileText,
  FolderKanban,
  Home,
  MessagesSquare,
  Mic,
  Monitor,
  Server,
  Settings,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { DashboardData } from "@/lib/types";

interface MainNavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

interface SoonNavItem {
  label: string;
  icon: LucideIcon;
}

const MAIN_NAV: MainNavItem[] = [
  { label: "Dashboard", href: "/", icon: Home },
  { label: "Conversa", href: "/conversa", icon: MessagesSquare },
  { label: "Voz", href: "/voz", icon: Mic },
  { label: "Monitor", href: "/monitor", icon: Monitor },
  { label: "Configuração", href: "/config", icon: Settings },
];

const SOON_NAV: SoonNavItem[] = [
  { label: "Memória", icon: Brain },
  { label: "Conhecimento", icon: Braces },
  { label: "Projetos", icon: FolderKanban },
  { label: "Documentos", icon: FileText },
  { label: "Tarefas", icon: Activity },
  { label: "Ferramentas", icon: Wrench },
  { label: "Docker", icon: Boxes },
  { label: "VPS", icon: Server },
  { label: "Cloudflare", icon: Cloud },
  { label: "Banco de Dados", icon: Database },
  { label: "Observação", icon: Eye },
  { label: "Automação", icon: Bot },
  { label: "Configurações", icon: Settings },
];

interface SidebarProps {
  data: DashboardData | null;
  onNavigate: (label: string) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

export default function Sidebar({ data, onNavigate, isOpen = false, onClose }: SidebarProps) {
  const pathname = usePathname();
  const version = data?.root?.version ?? "--";
  const ready = data?.readyz?.status === "ok";
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLinkClick = () => {
    if (onClose && window.innerWidth < 1024) {
      onClose();
    }
  };

  if (!mounted) {
    return (
      <aside className="glass sticky top-16 z-30 hidden h-[calc(100vh-4rem)] w-60 flex-col md:flex" />
    );
  }

  return (
    <>
      {window.innerWidth < 1024 && isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`
          glass sticky top-16 z-30 h-[calc(100vh-4rem)] w-60 flex-col md:flex
          ${window.innerWidth < 1024
            ? "fixed left-0 top-16 z-50 transform transition-transform duration-300 ease-in-out "
              + (isOpen ? "translate-x-0" : "-translate-x-full")
            : ""}
        `}
        role="navigation"
        aria-label="Navegação principal"
      >
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {MAIN_NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => { onNavigate?.(item.label); handleLinkClick(); }}
                className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-all duration-300 ${
                  active
                    ? "bg-[var(--color-prime)]/10 text-[var(--text-primary)] shadow-[inset_0_0_0_1px_var(--accent-muted)]"
                    : "text-[var(--text-secondary)] hover:bg-white/[0.03] hover:text-[var(--text-primary)]"
                }`}
              >
                <item.icon
                  className={`size-4 shrink-0 transition-colors ${
                    active
                      ? "text-[var(--accent)]"
                      : "text-[var(--text-secondary)] group-hover:text-[var(--accent)]"
                  }`}
                />
                <span className="truncate">{item.label}</span>
                {active && (
                  <span className="ml-auto size-1 rounded-full bg-[var(--accent)] shadow-[0_0_8px_var(--accent)]" />
                )}
              </Link>
            );
          })}

          <p className="px-3 pb-1 pt-4 font-mono-data text-[10px] font-semibold tracking-widest text-[var(--text-secondary)]">
            EM BREVE
          </p>
          {SOON_NAV.map((item) => (
            <button
              key={item.label}
              type="button"
              disabled
              aria-disabled="true"
              className="flex w-full cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2 text-[13px] text-[var(--text-secondary)] opacity-60"
            >
              <item.icon className="size-4 shrink-0 text-[var(--text-secondary)]" />
              <span className="truncate">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="border-t border-[var(--border)] p-3">
          <div className="glass rounded-xl p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Brain className="size-4 text-[var(--accent)]" />
                <span className="font-mono-data text-[11px] font-semibold tracking-widest text-[var(--text-primary)]">
                  NEGÃO CORE
                </span>
              </div>
              <span className="relative flex size-2">
                <span className="animate-ping-soft absolute inline-flex size-full rounded-full bg-[var(--color-ok)]" />
                <span className="relative inline-flex size-2 rounded-full bg-[var(--color-ok)]" />
              </span>
            </div>
            <div className="mt-3 space-y-1.5 font-mono-data text-[10px] text-[var(--text-secondary)]">
              <div className="flex justify-between">
                <span>VERSÃO</span>
                <span className="text-[var(--text-primary)]">v{version}</span>
              </div>
              <div className="flex justify-between">
                <span>STATUS</span>
                <span className={ready ? "text-[var(--color-ok)]" : "text-[var(--color-warn)]"}>
                  {ready ? "OPERACIONAL" : "PARCIAL"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>UPTIME</span>
                <span className="text-[var(--text-primary)]" id="core-uptime">
                  --:--:--
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}