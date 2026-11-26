"use client";

import {
  AlertTriangle,
  CircleHelp,
  OctagonAlert,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { useI18n } from "@/components/i18n/language-provider";
import { cn } from "@/lib/cn";
import type { MessageKey } from "@/lib/i18n/messages";
import type { RiskLevel } from "@/types/trust";

const riskMeta: Record<
  RiskLevel,
  { labelKey: MessageKey; Icon: LucideIcon; disc: string }
> = {
  safe: {
    labelKey: "risk.safe",
    Icon: ShieldCheck,
    disc: "bg-mint text-ink",
  },
  approaching: {
    labelKey: "risk.approaching",
    Icon: AlertTriangle,
    disc: "bg-amber text-ink",
  },
  "high-risk": {
    labelKey: "risk.high",
    Icon: OctagonAlert,
    disc: "bg-coral text-ink",
  },
  "needs-verification": {
    labelKey: "risk.needsVerification",
    Icon: CircleHelp,
    disc: "bg-lavender text-ink",
  },
};

type RiskIndicatorProps = {
  level: RiskLevel;
  className?: string;
};

export function RiskIndicator({ level, className }: RiskIndicatorProps) {
  const { t } = useI18n();
  const meta = riskMeta[level];
  const Icon = meta.Icon;

  return (
    <span
      className={cn(
        "inline-flex min-h-8 items-center gap-2 rounded-full border border-current/15 bg-black/5 py-1 ps-1 pe-3 text-sm font-semibold",
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
      {t(meta.labelKey)}
    </span>
  );
}
