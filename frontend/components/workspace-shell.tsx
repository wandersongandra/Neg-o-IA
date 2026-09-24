"use client";

import { useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Menu } from "lucide-react";
import Sidebar from "@/components/sidebar";
import TopBar from "@/components/top-bar";

export default function WorkspaceShell({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
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
        <main className="min-w-0 flex-1 overflow-x-hidden p-4 sm:p-5 md:p-6">
          <div className="mx-auto max-w-6xl space-y-6">
            <div className="flex items-center gap-3 lg:hidden">
              <button
                type="button"
                onClick={() => setSidebarOpen(true)}
                className="glass glass-hover interactive-control flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-[var(--text-secondary)]"
                aria-label="Abrir menu de navegação"
              >
                <Menu className="size-4" />
                Menu
              </button>
              <span className="truncate text-sm text-[var(--text-secondary)]">{title}</span>
            </div>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
