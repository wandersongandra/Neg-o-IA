"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/top-bar";
import Sidebar from "@/components/sidebar";

export default function ConversaShell({ children }: { children: ReactNode }) {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar data={null} onOpenPalette={() => router.push("/")} />
      <div className="flex flex-1">
        <Sidebar data={null} onNavigate={() => undefined} />
        {children}
      </div>
    </div>
  );
}
