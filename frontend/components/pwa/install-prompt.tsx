"use client";

import { useEffect, useState, useRef } from "react";
import { Download, X } from "lucide-react";

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
  prompt(): Promise<void>;
}

export function InstallPrompt() {
  const deferredPrompt = useRef<BeforeInstallPromptEvent | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    const isStandalone = window.matchMedia("(display-mode: standalone)").matches;
    const isIOSDevice = /iPad|iPhone|iPod/.test(navigator.userAgent) && !("MSStream" in window);
    setIsIOS(isIOSDevice);

    if (isStandalone || (navigator as Navigator & { standalone?: boolean }).standalone) {
      setIsInstalled(true);
      return;
    }

    if (
      isIOSDevice &&
      !localStorage.getItem("negao-install-dismissed")
    ) {
      setShowPrompt(true);
    }

    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      deferredPrompt.current = e as BeforeInstallPromptEvent;
      setShowPrompt(true);
    };

    const handleAppInstalled = () => {
      setIsInstalled(true);
      setShowPrompt(false);
      deferredPrompt.current = null;
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt.current) return;
    await deferredPrompt.current.prompt();
    const { outcome } = await deferredPrompt.current.userChoice;
    if (outcome === "accepted") {
      setShowPrompt(false);
      deferredPrompt.current = null;
    }
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    localStorage.setItem("negao-install-dismissed", Date.now().toString());
  };

  if (isInstalled || !showPrompt) return null;

  if (isIOS) {
    return (
      <div className="fixed bottom-4 left-4 right-4 md:bottom-6 md:left-auto md:right-6 md:w-[360px] z-50 animate-slide-up" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        <div className="glass rounded-2xl border border-[var(--border)] p-4 shadow-2xl">
          <div className="flex items-start gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--color-prime)] to-[var(--accent)] shrink-0">
              <Download className="size-5 text-[var(--bg-primary)]" strokeWidth={2.2} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-[var(--text-primary)]">Instalar NEGÃO AI</p>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                Toque em <strong>Compartilhar</strong> → <strong>Adicionar à Tela de Início</strong>
              </p>
            </div>
            <button
              onClick={handleDismiss}
              className="glass-hover flex size-8 items-center justify-center rounded-lg text-[var(--text-secondary)] shrink-0"
              aria-label="Fechar"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 md:bottom-6 md:left-auto md:right-6 md:w-[360px] z-50 animate-slide-up" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
      <div className="glass rounded-2xl border border-[var(--border)] p-4 shadow-2xl">
        <div className="flex items-start gap-3">
          <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--color-prime)] to-[var(--accent)] shrink-0">
            <Download className="size-5 text-[var(--bg-primary)]" strokeWidth={2.2} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-[var(--text-primary)]">Instalar NEGÃO AI</p>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Acesse o centro de comando direto da tela inicial
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleInstall}
              className="glass glass-hover flex items-center gap-2 rounded-xl bg-[var(--accent)]/20 px-4 py-2 text-sm font-medium text-[var(--accent)] transition-colors"
            >
              <Download className="size-3.5" />
              Instalar
            </button>
            <button
              onClick={handleDismiss}
              className="glass-hover flex size-8 items-center justify-center rounded-lg text-[var(--text-secondary)]"
              aria-label="Fechar"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function InstallButton({ onClick }: { onClick?: () => void }) {
  const deferredPrompt = useRef<BeforeInstallPromptEvent | null>(null);
  const [canInstall, setCanInstall] = useState(false);
  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    const isIOSDevice = /iPad|iPhone|iPod/.test(navigator.userAgent) && !("MSStream" in window);
    setIsIOS(isIOSDevice);

    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      deferredPrompt.current = e as BeforeInstallPromptEvent;
      setCanInstall(true);
    };

    const handleAppInstalled = () => {
      setCanInstall(false);
      deferredPrompt.current = null;
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, []);

  const handleClick = () => {
    if (deferredPrompt.current) {
      deferredPrompt.current.prompt();
      deferredPrompt.current.userChoice.then(({ outcome }) => {
        if (outcome === "accepted") {
          setCanInstall(false);
          deferredPrompt.current = null;
        }
      });
    } else if (isIOS || onClick) {
      onClick?.();
    }
  };

  if (!canInstall && !isIOS) return null;

  return (
    <button
      onClick={handleClick}
      className="glass glass-hover relative flex size-10 items-center justify-center rounded-xl text-[var(--text-secondary)]"
      aria-label={isIOS ? "Instruções de instalação iOS" : "Instalar NEGÃO AI"}
    >
      <Download className="size-4 transition-colors group-hover:text-[var(--accent)]" />
      {canInstall && !isIOS && (
        <span className="absolute -right-1 -top-1 size-2 rounded-full bg-[var(--accent)] ring-2 ring-[var(--bg-primary)]" />
      )}
    </button>
  );
}