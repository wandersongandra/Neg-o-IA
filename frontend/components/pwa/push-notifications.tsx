"use client";

import { useEffect, useState } from "react";
import { Bell, BellOff, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { subscribeToPush, unsubscribeFromPush, getNotificationPermissionState, isPushSupported } from "@/lib/push";

type PushStatus = "unsupported" | "denied" | "default" | "granted" | "subscribed" | "loading" | "error";

export function PushNotifications() {
  const [status, setStatus] = useState<PushStatus>("default");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    if (!isPushSupported()) {
      setStatus("unsupported");
      return;
    }

    const permission = getNotificationPermissionState();
    if (permission === "denied") {
      setStatus("denied");
      return;
    }

    if ("serviceWorker" in navigator) {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        setStatus("subscribed");
        return;
      }
    }

    setStatus(permission === "granted" ? "granted" : "default");
  };

  const handleSubscribe = async () => {
    const vapidPublicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
    if (!vapidPublicKey) {
      setError("VAPID public key not configured");
      setStatus("error");
      return;
    }

    setStatus("loading");
    setError(null);

    try {
      const result = await subscribeToPush(vapidPublicKey);
      if (result) {
        setStatus("subscribed");
      } else {
        const permission = getNotificationPermissionState();
        setStatus(permission === "denied" ? "denied" : "default");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to subscribe");
      setStatus("error");
    }
  };

  const handleUnsubscribe = async () => {
    setStatus("loading");
    try {
      await unsubscribeFromPush();
      setStatus("default");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unsubscribe");
      setStatus("error");
    }
  };

  const getIcon = () => {
    switch (status) {
      case "subscribed":
        return <CheckCircle2 className="size-4 text-[var(--color-ok)]" />;
      case "denied":
        return <BellOff className="size-4 text-[var(--color-danger)]" />;
      case "unsupported":
        return <BellOff className="size-4 text-[var(--text-muted)]" />;
      case "loading":
        return <Loader2 className="size-4 animate-spin text-[var(--accent)]" />;
      case "error":
        return <AlertCircle className="size-4 text-[var(--color-warn)]" />;
      default:
        return <Bell className="size-4" />;
    }
  };

  const getTooltip = () => {
    switch (status) {
      case "subscribed":
        return "Notificações ativadas";
      case "denied":
        return "Notificações bloqueadas (ative nas configurações do navegador)";
      case "unsupported":
        return "Notificações não suportadas neste navegador";
      case "loading":
        return "Configurando...";
      case "error":
        return `Erro: ${error}`;
      case "granted":
        return "Permissão concedida - clique para ativar";
      default:
        return "Ativar notificações";
    }
  };

  const handleClick = () => {
    if (status === "subscribed") {
      handleUnsubscribe();
    } else if (status === "default" || status === "granted") {
      handleSubscribe();
    }
  };

  if (status === "unsupported") return null;

  return (
    <button
      onClick={handleClick}
      disabled={status === "loading" || status === "denied"}
      className={`glass glass-hover relative flex size-10 items-center justify-center rounded-xl transition-colors ${
        status === "subscribed"
          ? "text-[var(--color-ok)]"
          : status === "denied" || status === "error"
          ? "text-[var(--text-muted)] cursor-not-allowed"
          : "text-[var(--text-secondary)]"
      }`}
      aria-label={getTooltip()}
      title={getTooltip()}
    >
      {getIcon()}
      {status === "subscribed" && (
        <span className="absolute -right-1 -top-1 size-2 rounded-full bg-[var(--color-ok)] ring-2 ring-[var(--bg-primary)]" />
      )}
    </button>
  );
}