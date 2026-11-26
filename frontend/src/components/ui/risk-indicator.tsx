import {
  AlertTriangle,
  CircleHelp,
  OctagonAlert,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";
import type { RiskLevel } from "@/types/trust";

const riskMeta: Record<
  RiskLevel,
  { label: string; Icon: LucideIcon; disc: string }
> = {
  safe: {
    label: "Safe",
    Icon: ShieldCheck,
    disc: "bg-mint text-ink",
  },
  approaching: {
    label: "Approaching",
    Icon: AlertTriangle,
    disc: "bg-amber text-ink",
  },
  "high-risk": {
    label: "High risk",
    Icon: OctagonAlert,
    disc: "bg-coral text-ink",
  },
  "needs-verification": {
    label: "Needs verification",
    Icon: CircleHelp,
    disc: "bg-lavender text-ink",
  },
};

type RiskIndicatorProps = {
  level: RiskLevel;
  className?: string;
};

export function RiskIndicator({ level, className }: RiskIndicatorProps) {
  const meta = riskMeta[level];
  const Icon = meta.Icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-current/15 bg-black/5 py-1 pr-3 pl-1 text-sm font-semibold",
        className,
      )}
    >
      <span
        className={cn(
          "grid h-7 w-7 place-items-center rounded-full",
          meta.disc,
        )}
        aria-hidden="true"
      >
        <Icon className="h-4 w-4" />
      </span>
      {meta.label}
    </span>
  );
}
