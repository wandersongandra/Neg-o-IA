"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X, CheckCircle2, AlertCircle, Info } from "lucide-react";

export type ToastVariant = "default" | "destructive" | "success";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
  duration?: number;
}

interface ToastContextType {
  toast: (props: Omit<Toast, "id">) => string;
  dismiss: (id: string) => void;
  dismissAll: () => void;
  toasts: Toast[];
}

const ToastContext = createContext<ToastContextType | null>(null);

function generateId() {
  return Math.random().toString(36).substring(2, 10);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((props: Omit<Toast, "id">) => {
    const id = generateId();
    const newToast: Toast = { ...props, id };
    setToasts((prev) => [...prev, newToast]);
    return id;
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  const value = { toast: addToast, dismiss, dismissAll, toasts };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastPortal toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

function ToastPortal({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  if (typeof window === "undefined") return null;

  return createPortal(
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2 pointer-events-none"
      style={{ maxWidth: "400px", paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>,
    document.body
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const duration = toast.duration ?? 5000;
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(() => onDismiss(toast.id), 300);
    }, duration);
    return () => clearTimeout(timer);
  }, [toast, onDismiss]);

  const variantStyles: Record<ToastVariant, string> = {
    default: "border-[var(--accent)]/30 bg-[var(--accent-muted)]",
    destructive: "border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10",
    success: "border-[var(--color-ok)]/30 bg-[var(--color-ok)]/10",
  };

  const iconComponents: Record<ToastVariant, React.ReactNode> = {
    default: <Info className="size-4 text-[var(--accent)]" />,
    destructive: <AlertCircle className="size-4 text-[var(--color-danger)]" />,
    success: <CheckCircle2 className="size-4 text-[var(--color-ok)]" />,
  };

  if (!visible) return null;

  return (
    <div
      className={`glass glass-hover pointer-events-auto flex items-start gap-3 rounded-xl p-4 animate-fade-in ${variantStyles[toast.variant]}`}
    >
      <div className="shrink-0 mt-0.5">{iconComponents[toast.variant]}</div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-[var(--text-primary)]">{toast.title}</p>
        {toast.description && (
          <p className="mt-0.5 text-sm text-[var(--text-secondary)]">{toast.description}</p>
        )}
      </div>
      <button
        onClick={() => {
          setVisible(false);
          setTimeout(() => onDismiss(toast.id), 300);
        }}
        className="shrink-0 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
        aria-label="Fechar"
      >
        <X className="size-4" />
      </button>
    </div>
  );
}