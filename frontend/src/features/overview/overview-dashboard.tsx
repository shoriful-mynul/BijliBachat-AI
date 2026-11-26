"use client";

import { useI18n } from "@/components/i18n/language-provider";
import { CliffGuardPreview } from "@/components/dashboard/cliff-guard-preview";
import { HistorySummary } from "@/features/history/history-summary";
import { PredictionSummary } from "@/features/prediction/prediction-summary";
import { ConsumptionSummary } from "@/components/dashboard/consumption-summary";
import { EstimatedBillCard } from "@/components/dashboard/estimated-bill-card";
import { NextBestAction } from "@/components/dashboard/next-best-action";
import { RecentReading } from "@/components/dashboard/recent-reading";
import { WelcomeSection } from "@/components/dashboard/welcome-section";

export function OverviewDashboard() {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-5">
      <WelcomeSection />
      <PredictionSummary />
      <HistorySummary />
      <p className="text-sm leading-6 text-muted">{t("dashboard.sampleBanner")}</p>
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <EstimatedBillCard />
        </div>
        <div className="lg:col-span-2">
          <CliffGuardPreview />
        </div>
      </div>
      <ConsumptionSummary />
      <div className="grid gap-4 lg:grid-cols-2">
        <NextBestAction />
        <RecentReading />
      </div>
    </div>
  );
}
