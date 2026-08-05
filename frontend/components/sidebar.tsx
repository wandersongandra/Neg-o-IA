"use client";

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
  Server,
  Settings,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { DashboardData } from "@/lib/types";

interface NavItem {
  label: string;
  icon: LucideIcon;
  active?: boolean;
}

const NAV: NavItem[] = [
  { label: "Home", icon: Home, active: true },
  { label: "Conversa", icon: MessagesSquare },
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
}

export default function Sidebar({ data, onNavigate }: SidebarProps) {
  const version = data?.root?.version ?? "--";
  const ready = data?.readyz?.status === "ok";

  return (
    <aside className="glass sticky top-16 z-30 hidden h-[calc(100vh-4rem)] w-60 flex-col md:flex">
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
        {NAV.map((item) => (
          <button
            key={item.label}
            onClick={() => onNavigate(item.label)}
            className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-all duration-300 ${
              item.active
                ? "bg-[#3B82F6]/10 text-[#F8FAFC] shadow-[inset_0_0_0_1px_rgba(59,130,246,0.25)]"
                : "text-[#94A3B8] hover:bg-white/[0.03] hover:text-[#F8FAFC]"
            }`}
          >
            <item.icon
              className={`size-4 shrink-0 transition-colors ${
                item.active
                  ? "text-[#00D4FF]"
                  : "text-[#64748B] group-hover:text-[#00D4FF]"
              }`}
            />
            <span className="truncate">{item.label}</span>
            {item.active && (
              <span className="ml-auto size-1 rounded-full bg-[#00D4FF] shadow-[0_0_8px_#00D4FF]" />
            )}
          </button>
        ))}
      </nav>

      <div className="border-t border-white/[0.06] p-3">
        <div className="glass rounded-xl p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className="size-4 text-[#00D4FF]" />
              <span className="font-mono-data text-[11px] font-semibold tracking-widest text-[#F8FAFC]">
                NEGÃO CORE
              </span>
            </div>
            <span className="relative flex size-2">
              <span className="animate-ping-soft absolute inline-flex size-full rounded-full bg-[#22C55E]" />
              <span className="relative inline-flex size-2 rounded-full bg-[#22C55E]" />
            </span>
          </div>
          <div className="mt-3 space-y-1.5 font-mono-data text-[10px] text-[#94A3B8]">
            <div className="flex justify-between">
              <span>VERSÃO</span>
              <span className="text-[#F8FAFC]">v{version}</span>
            </div>
            <div className="flex justify-between">
              <span>STATUS</span>
              <span className={ready ? "text-[#22C55E]" : "text-[#F59E0B]"}>
                {ready ? "OPERACIONAL" : "PARCIAL"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>UPTIME</span>
              <span className="text-[#F8FAFC]" id="core-uptime">
                --:--:--
              </span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
