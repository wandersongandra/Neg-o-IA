"use client";

import { useEffect } from "react";
import { ToastProvider } from "@/components/ui/toast";
import { AvatarProvider } from "@/components/avatar/avatar-context";

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    localStorage.setItem("sophie-theme", "ultron");
    document.documentElement.dataset.theme = "ultron";
  }, []);


  return (
    <AvatarProvider>
      <ToastProvider>
        {children}
      </ToastProvider>
    </AvatarProvider>
  );
}
