import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { SectionHeader } from "@/components/ui/section-header";
import { demoOverview } from "@/features/overview/demo-data";
import { formatGrouped } from "@/lib/format";

export function RecentReading() {
  const { reading } = demoOverview;

  return (
    <Card className="h-full">
      <SectionHeader
        title="Latest manual checkpoint"
        description="Submitted by the household. This is not a live reading from the meter."
        actions={
          <>
            <Badge>Demo data</Badge>
            <DataTrustChip status="estimated" />
          </>
        }
      />
      <p className="mt-5 font-mono text-3xl font-medium tracking-tight tabular-nums">
        {formatGrouped(reading.registerKwh)}
        <span className="ml-2 text-base font-normal text-muted">kWh</span>
      </p>
      <dl className="mt-4 grid gap-3 text-sm">
        <div>
          <dt className="text-muted">Last updated in the sample</dt>
          <dd className="mt-1 font-medium">{reading.submittedOn}</dd>
        </div>
        <div>
          <dt className="text-muted">Previous checkpoint</dt>
          <dd className="mt-1 font-medium">Not on file in this sample</dd>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <dt className="text-muted">Live feed</dt>
          <dd>
            <DataTrustChip status="unavailable" />
          </dd>
        </div>
      </dl>
    </Card>
  );
}
