"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { ToastProvider } from "@/components/ui/toast";
import { AvatarProvider } from "@/components/avatar/avatar-context";

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const stored = localStorage.getItem("negao-theme") as "azul" | "esmeralda" | "magenta" | null;
    if (stored) {
      document.documentElement.dataset.theme = stored;
    } else {
      document.documentElement.dataset.theme = "azul";
    }
  }, []);

  const pathname = usePathname();

  useEffect(() => {
    if (!document.startViewTransition) return;

    const handleLinkClick = (e: MouseEvent) => {
      const anchor = e.target instanceof HTMLAnchorElement ? e.target : (e.target as HTMLElement).closest("a");
      if (!anchor) return;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("http") || anchor.target === "_blank") return;
      if (anchor.origin !== window.location.origin) return;

      e.preventDefault();
      document.startViewTransition(() => {
        window.location.href = href;
      });
    };

    document.addEventListener("click", handleLinkClick);
    return () => document.removeEventListener("click", handleLinkClick);
  }, [pathname]);

  return (
    <AvatarProvider>
      <ToastProvider>
        {children}
      </ToastProvider>
    </AvatarProvider>
  );
}