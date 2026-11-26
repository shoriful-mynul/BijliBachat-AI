import { Shirt } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { demoOverview } from "@/features/overview/demo-data";
import { formatPkr } from "@/lib/format";

export function NextBestAction() {
  const { action } = demoOverview;

  return (
    <Card variant="ice" className="h-full">
      <div className="flex items-start gap-3">
        <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-white/70 text-ink">
          <Shirt className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <h2 className="font-display text-base font-semibold leading-snug">
            Next best action
          </h2>
          <p className="ice-muted mt-1 text-sm leading-6">{action.detail}</p>
        </div>
      </div>
      <p className="mt-4 font-display text-lg font-semibold leading-snug">
        {action.title}
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Badge>Demo data</Badge>
        <DataTrustChip status="estimated" />
      </div>
      <p className="mt-3 font-display text-2xl font-semibold tabular-nums">
        {formatPkr(action.illustrativeSavingPkr)}
      </p>
      <p className="ice-muted mt-2 text-sm leading-6">
        Sample illustration only. No saving has been calculated for this
        household.
      </p>
    </Card>
  );
}
