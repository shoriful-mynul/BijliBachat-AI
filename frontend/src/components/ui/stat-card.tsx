import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import type { DataTrustStatus } from "@/types/trust";

type StatCardProps = {
  label: string;
  value: string;
  detail?: string;
  trust?: DataTrustStatus;
  demo?: boolean;
  valueClassName?: string;
};

export function StatCard({
  label,
  value,
  detail,
  trust,
  demo = false,
  valueClassName,
}: StatCardProps) {
  return (
    <Card as="article" className="flex h-full flex-col">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-muted">{label}</p>
        {demo ? <Badge>Demo data</Badge> : null}
      </div>
      <p
        className={
          valueClassName ??
          "mt-3 font-display text-2xl font-semibold tracking-tight tabular-nums"
        }
      >
        {value}
      </p>
      {detail ? <p className="mt-1 text-sm leading-6 text-muted">{detail}</p> : null}
      {trust ? (
        <div className="mt-4">
          <DataTrustChip status={trust} />
        </div>
      ) : null}
    </Card>
  );
}
