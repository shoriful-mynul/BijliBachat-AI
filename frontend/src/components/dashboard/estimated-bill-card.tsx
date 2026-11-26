"use client";

import { useI18n } from "@/components/i18n/language-provider";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { SectionHeader } from "@/components/ui/section-header";
import { demoOverview } from "@/features/overview/demo-data";
import { formatPkr } from "@/lib/format";

export function EstimatedBillCard() {
  const { t } = useI18n();
  return (
    <Card className="accent-rail h-full">
      <SectionHeader
        title={t("dashboard.billTitle")}
        description={t("dashboard.billDescription")}
        actions={
          <>
            <Badge>{t("common.demoData")}</Badge>
            <DataTrustChip status="estimated" />
          </>
        }
      />
      <p className="mt-5 font-display text-4xl font-semibold tracking-tight tabular-nums">
        {formatPkr(demoOverview.bill.amountPkr)}
      </p>
      <p className="mt-3 max-w-xl text-sm leading-6 text-muted">
        {t("dashboard.billDetail", { cycle: demoOverview.cycle.label })}
      </p>
    </Card>
  );
}
