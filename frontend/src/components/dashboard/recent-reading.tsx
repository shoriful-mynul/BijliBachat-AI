"use client";

import { useI18n } from "@/components/i18n/language-provider";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { SectionHeader } from "@/components/ui/section-header";
import { demoOverview } from "@/features/overview/demo-data";
import { formatGrouped } from "@/lib/format";

export function RecentReading() {
  const { t } = useI18n();
  const { reading } = demoOverview;

  return (
    <Card className="h-full">
      <SectionHeader
        title={t("dashboard.readingTitle")}
        description={t("dashboard.readingDescription")}
        actions={
          <>
            <Badge>{t("common.demoData")}</Badge>
            <DataTrustChip status="estimated" />
          </>
        }
      />
      <p className="mt-5 font-mono text-3xl font-medium tracking-tight tabular-nums">
        {formatGrouped(reading.registerKwh)}
        <span className="ms-2 text-base font-normal text-muted">kWh</span>
      </p>
      <dl className="mt-4 grid gap-3 text-sm">
        <div>
          <dt className="text-muted">{t("dashboard.readingUpdated")}</dt>
          <dd className="mt-1 font-medium">{reading.submittedOn}</dd>
        </div>
        <div>
          <dt className="text-muted">{t("dashboard.previousCheckpoint")}</dt>
          <dd className="mt-1 font-medium">{t("dashboard.previousMissing")}</dd>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <dt className="text-muted">{t("dashboard.liveFeed")}</dt>
          <dd>
            <DataTrustChip status="unavailable" />
          </dd>
        </div>
      </dl>
    </Card>
  );
}
