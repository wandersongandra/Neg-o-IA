"use client";

import { useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Menu } from "lucide-react";
import TopBar from "@/components/top-bar";
import Sidebar from "@/components/sidebar";

export default function ConversaShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar data={null} onOpenPalette={() => router.push("/")} />
      <div className="flex flex-1">
        <Sidebar
          data={null}
          onNavigate={() => undefined}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
        <main className="flex flex-1 flex-col overflow-hidden">
          <div className="p-4 pb-0 lg:hidden">
            <button
              className="glass glass-hover interactive-control flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              onClick={() => setSidebarOpen(true)}
              aria-label="Abrir menu de navegação"
              aria-expanded={sidebarOpen}
            >
              <Menu className="size-4" />
              Menu
            </button>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
