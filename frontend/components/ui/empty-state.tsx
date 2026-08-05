"use client";

import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className = "" }: EmptyStateProps) {
  return (
    <div className={`glass flex flex-col items-center justify-center gap-4 rounded-2xl p-8 text-center ${className}`}>
      <div className="flex size-16 items-center justify-center rounded-2xl bg-[var(--accent-muted)] ring-1 ring-[var(--accent)]/30">
        <Icon className="size-7 text-[var(--accent)]" />
      </div>
      <div className="space-y-1">
        <h3 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h3>
        <p className="text-sm text-[var(--text-secondary)] max-w-sm">{description}</p>
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function EmptyStateInline({ icon: Icon, title, description, action, className = "" }: EmptyStateProps) {
  return (
    <div className={`glass flex items-center gap-4 rounded-xl p-6 ${className}`}>
      <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-muted)] ring-1 ring-[var(--accent)]/30">
        <Icon className="size-5 text-[var(--accent)]" />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold text-[var(--text-primary)]">{title}</h3>
        <p className="text-sm text-[var(--text-secondary)]">{description}</p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}