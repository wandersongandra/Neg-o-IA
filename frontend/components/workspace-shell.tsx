"use client";

import { useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Menu } from "lucide-react";
import Sidebar from "@/components/sidebar";
import TopBar from "@/components/top-bar";

export default function WorkspaceShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar
        data={null}
        commandLabel="Voltar ao centro de comando"
        onOpenPalette={() => router.push("/")}
      />
      <div className="flex flex-1">
        <Sidebar
          data={null}
          onNavigate={() => undefined}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
        <main className="min-w-0 flex-1 space-y-6 overflow-x-hidden p-4 sm:p-5 md:p-6">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="glass glass-hover interactive-control flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-[var(--text-secondary)] lg:hidden"
            aria-label="Abrir menu de navegação"
            aria-expanded={sidebarOpen}
            aria-controls="sidebar"
          >
            <Menu className="size-4" />
            Menu
          </button>
          <header className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
              {title}
            </h1>
            <p className="text-sm text-[var(--text-secondary)]">{description}</p>
          </header>
          {children}
        </main>
      </div>
    </div>
  );
}
