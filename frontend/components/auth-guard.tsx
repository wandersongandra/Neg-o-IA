"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

export default function AuthGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [state, setState] = useState<"checking" | "authenticated" | "unauthenticated">(
    pathname === "/login" ? "authenticated" : "checking",
  );

  useEffect(() => {
    if (pathname === "/login") {
      setState("authenticated");
      return;
    }
    let cancelled = false;
    void fetch("/api/auth/me", { cache: "no-store" })
      .then((response) => {
        if (cancelled) return;
        if (response.ok) setState("authenticated");
        else {
          setState("unauthenticated");
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setState("unauthenticated");
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [pathname, router]);

  if (state !== "authenticated") {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-[var(--bg)] p-6">
        <p className="font-mono-data text-xs uppercase tracking-[0.25em] text-[var(--text-secondary)]">
          Validando identidade…
        </p>
      </main>
    );
  }
  return <>{children}</>;
}
