"use client";

import type { ReactNode } from "react";
import TopBar from "@/components/top-bar";
import Sidebar from "@/components/sidebar";

export default function ConversaShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar data={null} onOpenPalette={() => undefined} />
      <div className="flex flex-1">
        <Sidebar data={null} onNavigate={() => undefined} />
        {children}
      </div>
    </div>
  );
}
