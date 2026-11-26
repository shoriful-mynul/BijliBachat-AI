"use client";

import { useI18n } from "@/components/i18n/language-provider";
import { ConsumptionChart } from "@/components/dashboard/consumption-chart";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { SectionHeader } from "@/components/ui/section-header";
import { StatCard } from "@/components/ui/stat-card";
import { demoOverview, demoUnitsSoFar } from "@/features/overview/demo-data";
import { formatGrouped } from "@/lib/format";

export function ConsumptionSummary() {
  const { t } = useI18n();
  const { cycle } = demoOverview;

  return (
    <section className="flex flex-col gap-4" aria-labelledby="consumption-title">
      <SectionHeader
        titleId="consumption-title"
        title={t("dashboard.consumptionTitle")}
        description={t("dashboard.consumptionDescription")}
        actions={
          <>
            <Badge>{t("common.demoData")}</Badge>
            <DataTrustChip status="estimated" />
          </>
        }
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard
          label={t("dashboard.unitsSoFar")}
          value={`${formatGrouped(demoUnitsSoFar)} kWh`}
          detail={t("dashboard.unitsDetail")}
          trust="estimated"
          demo
          valueClassName="mt-3 font-mono text-2xl font-medium tracking-tight tabular-nums"
        />
        <StatCard
          label={t("dashboard.cycleDay")}
          value={t("dashboard.dayOf", { day: cycle.day, length: cycle.length })}
          detail={cycle.label}
          trust="estimated"
          demo
        />
        <StatCard
          label={t("dashboard.latestDay")}
          value="18 Nov"
          detail={cycle.illustratedThrough}
          trust="estimated"
          demo
        />
      </div>
      <Card>
        <div className="mb-4">
          <h3 className="font-display text-base font-semibold">{t("dashboard.dailyUse")}</h3>
          <p className="mt-1 text-sm leading-6 text-muted">{t("dashboard.dailyUseDetail")}</p>
          <div className="mt-4">
            <div className="mb-2 flex items-center justify-between gap-3 text-sm">
              <span>{t("dashboard.progress")}</span>
              <span className="font-mono tabular-nums text-muted">
                {t("dashboard.dayOf", { day: cycle.day, length: cycle.length })}
              </span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-raised"
              role="progressbar"
              aria-valuemin={1}
              aria-valuemax={cycle.length}
              aria-valuenow={cycle.day}
              aria-valuetext={t("dashboard.progressValue", { day: cycle.day, length: cycle.length })}
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
