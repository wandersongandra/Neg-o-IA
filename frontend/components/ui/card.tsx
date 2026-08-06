import React from "react";
import type { ReactNode } from "react";

type CardVariant = "elevated" | "outlined" | "filled";

interface CardProps {
  children: ReactNode;
  variant?: CardVariant;
  interactive?: boolean;
  className?: string;
  onClick?: () => void;
}

interface CardHeaderProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  action?: ReactNode;
}

interface CardBodyProps {
  children: ReactNode;
  className?: string;
}

interface CardFooterProps {
  children: ReactNode;
  className?: string;
}

const variantStyles: Record<CardVariant, string> = {
  elevated:
    "glass glass-hover animate-fade-up rounded-2xl p-4 backdrop-blur-base bg-gradient-to-br from-white/[0.08] to-white/[0.02]",
  outlined:
    "rounded-2xl p-4 border border-[var(--border)] bg-transparent hover:border-[var(--accent-muted)] transition-colors duration-300",
  filled:
    "rounded-2xl p-4 bg-[var(--bg-secondary)] border border-[var(--border)] hover:bg-[var(--bg-secondary)]/80 transition-colors duration-300",
};

export const Card = React.forwardRef<
  HTMLDivElement,
  CardProps
>(({ variant = "elevated", interactive = false, className, onClick, children }, ref) => {
  const interactiveStyles = interactive
    ? "cursor-pointer hover:shadow-lg"
    : "";
  const customClasses = className || "";

  return (
    <div
      ref={ref}
      className={`${variantStyles[variant]} ${interactiveStyles} ${customClasses}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
});

Card.displayName = "Card";

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  subtitle,
  icon,
  action,
}) => (
  <div className="mb-4 flex items-center justify-between gap-3">
    <div className="flex items-center gap-3">
      {icon && <div className="flex-shrink-0">{icon}</div>}
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] truncate">
          {title}
        </h3>
        {subtitle && (
          <p className="font-mono-data text-xs text-[var(--text-secondary)] truncate">
            {subtitle}
          </p>
        )}
      </div>
    </div>
    {action && <div className="flex-shrink-0">{action}</div>}
  </div>
);

CardHeader.displayName = "CardHeader";

export const CardBody: React.FC<CardBodyProps> = ({ children, className }) => (
  <div className={className || ""}>{children}</div>
);

CardBody.displayName = "CardBody";

export const CardFooter: React.FC<CardFooterProps> = ({ children, className }) => (
  <div className={`mt-4 border-t border-[var(--border)] pt-4 ${className || ""}`}>
    {children}
  </div>
);

CardFooter.displayName = "CardFooter";

export default Card;
