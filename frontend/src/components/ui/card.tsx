import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type CardProps = {
  as?: "section" | "article" | "div";
  variant?: "default" | "raised" | "ice";
  className?: string;
  children: ReactNode;
};

const variants = {
  default: "bg-card text-foreground",
  raised: "bg-raised text-foreground",
  ice: "bg-ice text-ink",
} as const;

export function Card({
  as = "section",
  variant = "default",
  className,
  children,
}: CardProps) {
  const Component = as;
  return (
    <Component
      data-surface={variant === "ice" ? "ice" : undefined}
      className={cn(
        "surface rounded-2xl border p-4 md:p-5",
        variant === "ice" ? "border-ink/10" : "border-line",
        variants[variant],
        className,
      )}
    >
      {children}
    </Component>
  );
}
