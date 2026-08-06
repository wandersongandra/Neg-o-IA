import React from "react";
import type { ReactNode } from "react";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info";
type BadgeSize = "sm" | "md" | "lg";

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  icon?: ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default:
    "bg-[var(--color-prime)]/10 text-[var(--accent)] border border-[var(--color-prime)]/30",
  success:
    "bg-[var(--color-ok)]/10 text-[var(--color-ok)] border border-[var(--color-ok)]/30",
  warning:
    "bg-[var(--color-warn)]/10 text-[var(--color-warn)] border border-[var(--color-warn)]/30",
  danger:
    "bg-[var(--color-danger)]/10 text-[var(--color-danger)] border border-[var(--color-danger)]/30",
  info:
    "bg-[var(--accent)]/10 text-[var(--accent)] border border-[var(--accent)]/30",
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: "px-2 py-1 text-xs font-medium",
  md: "px-3 py-1.5 text-xs font-semibold",
  lg: "px-4 py-2 text-sm font-semibold",
};

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ variant = "default", size = "md", icon, className, children }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center gap-1.5 rounded-full font-mono-data whitespace-nowrap";
    const variantStyle = variantStyles[variant];
    const sizeStyle = sizeStyles[size];
    const customClasses = className || "";

    return (
      <div
        ref={ref}
        className={`${baseStyles} ${variantStyle} ${sizeStyle} ${customClasses}`}
      >
        {icon && <span className="flex-shrink-0">{icon}</span>}
        {children}
      </div>
    );
  },
);

Badge.displayName = "Badge";

export default Badge;
