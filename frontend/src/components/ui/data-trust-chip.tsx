import {
  BadgeCheck,
  Calculator,
  CircleDashed,
  CircleOff,
  ScanText,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";
import type { DataTrustStatus } from "@/types/trust";

const trustMeta: Record<
  DataTrustStatus,
  { label: string; Icon: LucideIcon; disc: string }
> = {
  verified: {
    label: "Verified",
    Icon: BadgeCheck,
    disc: "bg-teal text-ink",
  },
  calculated: {
    label: "Calculated",
    Icon: Calculator,
    disc: "bg-aqua text-ink",
  },
  extracted: {
    label: "Extracted",
    Icon: ScanText,
    disc: "bg-lavender text-ink",
  },
  estimated: {
    label: "Estimated",
    Icon: CircleDashed,
    disc: "bg-amber text-ink",
  },
  unavailable: {
    label: "Unavailable",
    Icon: CircleOff,
    disc: "bg-ink text-ice",
  },
};

type DataTrustChipProps = {
  status: DataTrustStatus;
  className?: string;
};

export function DataTrustChip({ status, className }: DataTrustChipProps) {
  const meta = trustMeta[status];
  const Icon = meta.Icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-current/15 bg-black/5 py-1 pr-3 pl-1 text-sm font-medium",
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
      {meta.label}
    </span>
  );
}
