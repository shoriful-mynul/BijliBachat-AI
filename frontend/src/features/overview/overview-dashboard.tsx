import { CliffGuardPreview } from "@/components/dashboard/cliff-guard-preview";
import { PredictionSummary } from "@/features/prediction/prediction-summary";
import { ConsumptionSummary } from "@/components/dashboard/consumption-summary";
import { EstimatedBillCard } from "@/components/dashboard/estimated-bill-card";
import { NextBestAction } from "@/components/dashboard/next-best-action";
import { RecentReading } from "@/components/dashboard/recent-reading";
import { WelcomeSection } from "@/components/dashboard/welcome-section";

export function OverviewDashboard() {
  return (
    <div className="flex flex-col gap-5">
      <WelcomeSection />
      <PredictionSummary />
      <p className="text-sm leading-6 text-muted">
        The cards below are the labeled sample overview. They are not calculated from your checkpoints.
      </p>
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
