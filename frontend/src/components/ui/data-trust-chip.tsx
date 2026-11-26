"use client";

import {
  BadgeCheck,
  Calculator,
  CircleDashed,
  CircleOff,
  ScanText,
  type LucideIcon,
} from "lucide-react";
import { useI18n } from "@/components/i18n/language-provider";
import { cn } from "@/lib/cn";
import type { MessageKey } from "@/lib/i18n/messages";
import type { DataTrustStatus } from "@/types/trust";

const trustMeta: Record<
  DataTrustStatus,
  { labelKey: MessageKey; Icon: LucideIcon; disc: string }
> = {
  verified: {
    labelKey: "trust.verified",
    Icon: BadgeCheck,
    disc: "bg-teal text-ink",
  },
  calculated: {
    labelKey: "trust.calculated",
    Icon: Calculator,
    disc: "bg-aqua text-ink",
  },
  extracted: {
    labelKey: "trust.extracted",
    Icon: ScanText,
    disc: "bg-lavender text-ink",
  },
  estimated: {
    labelKey: "trust.estimated",
    Icon: CircleDashed,
    disc: "bg-amber text-ink",
  },
  unavailable: {
    labelKey: "trust.unavailable",
    Icon: CircleOff,
    disc: "bg-ink text-ice",
  },
};

type DataTrustChipProps = {
  status: DataTrustStatus;
  className?: string;
};

export function DataTrustChip({ status, className }: DataTrustChipProps) {
  const { t } = useI18n();
  const meta = trustMeta[status];
  const Icon = meta.Icon;

  return (
    <span
      className={cn(
        "inline-flex min-h-8 items-center gap-2 rounded-full border border-current/15 bg-black/5 py-1 ps-1 pe-3 text-sm font-medium",
        className,
      )}
    >
      <span
        className={cn(
          "grid h-6 w-6 place-items-center rounded-full",
          meta.disc,
        )}
        aria-hidden="true"
      >
        <Icon className="h-3.5 w-3.5" />
      </span>
      {t(meta.labelKey)}
    </span>
  );
}
