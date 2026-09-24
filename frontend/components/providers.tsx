"use client";

import { useEffect } from "react";
import { ToastProvider } from "@/components/ui/toast";
import { AvatarProvider } from "@/components/avatar/avatar-context";

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const stored = localStorage.getItem("sophie-theme") as "azul" | "esmeralda" | "magenta" | null;
    if (stored) {
      document.documentElement.dataset.theme = stored;
    } else {
      document.documentElement.dataset.theme = "azul";
    }
  }, []);


  return (
    <AvatarProvider>
      <ToastProvider>
        {children}
      </ToastProvider>
    </AvatarProvider>
  );
}
