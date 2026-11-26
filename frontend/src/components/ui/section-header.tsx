import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type SectionHeaderProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
  as?: "h2" | "h3";
  titleId?: string;
};

export function SectionHeader({
  title,
  description,
  actions,
  className,
  as = "h2",
  titleId,
}: SectionHeaderProps) {
  const Title = as;

  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="min-w-0">
        <Title id={titleId} className="font-display text-base font-semibold leading-snug">
          {title}
        </Title>
        {description ? (
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
