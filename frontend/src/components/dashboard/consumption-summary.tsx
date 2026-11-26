import { ConsumptionChart } from "@/components/dashboard/consumption-chart";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { SectionHeader } from "@/components/ui/section-header";
import { StatCard } from "@/components/ui/stat-card";
import { demoOverview, demoUnitsSoFar } from "@/features/overview/demo-data";
import { formatGrouped } from "@/lib/format";

export function ConsumptionSummary() {
  const { cycle } = demoOverview;

  return (
    <section className="flex flex-col gap-4" aria-labelledby="consumption-title">
      <SectionHeader
        titleId="consumption-title"
        title="Consumption"
        description="Authored daily use for part of the sample cycle. These points are not a meter feed."
        actions={
          <>
            <Badge>Demo data</Badge>
            <DataTrustChip status="estimated" />
          </>
        }
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard
          label="Sample units so far"
          value={`${formatGrouped(demoUnitsSoFar)} kWh`}
          detail="Authored total for the bars below."
          trust="estimated"
          demo
          valueClassName="mt-3 font-mono text-2xl font-medium tracking-tight tabular-nums"
        />
        <StatCard
          label="Sample cycle day"
          value={`${cycle.day} of ${cycle.length}`}
          detail={cycle.label}
          trust="estimated"
          demo
        />
        <StatCard
          label="Latest illustrated day"
          value="18 Nov"
          detail={cycle.illustratedThrough}
          trust="estimated"
          demo
        />
      </div>
      <Card>
        <div className="mb-4">
          <h3 className="font-display text-base font-semibold">Daily use</h3>
          <p className="mt-1 text-sm leading-6 text-muted">
            Demo data, in kilowatt-hours, from 1 to 18 November. No tariff line
            is drawn.
          </p>
          <div className="mt-4">
            <div className="mb-2 flex items-center justify-between gap-3 text-sm">
              <span>Sample cycle progress</span>
              <span className="font-mono tabular-nums text-muted">
                Day {cycle.day} of {cycle.length}
              </span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-raised"
              role="progressbar"
              aria-valuemin={1}
              aria-valuemax={cycle.length}
              aria-valuenow={cycle.day}
              aria-valuetext={`Day ${cycle.day} of ${cycle.length} in the sample cycle`}
            >
              <div
                className="h-full rounded-full bg-teal"
                style={{ width: `${cycle.progressPercent}%` }}
              />
            </div>
          </div>
        </div>
        <ConsumptionChart />
      </Card>
    </section>
  );
}
