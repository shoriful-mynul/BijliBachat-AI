"use client";

import { useI18n } from "@/components/i18n/language-provider";
import { Badge } from "@/components/ui/badge";
import { demoOverview } from "@/features/overview/demo-data";

export function WelcomeSection() {
  const { t } = useI18n();
  const { household, cycle } = demoOverview;

  return (
    <section aria-labelledby="welcome-title">
      <p className="text-sm text-muted">
        {t("dashboard.samplePlace", { place: household.place })}
      </p>
      <h2
        id="welcome-title"
        className="mt-1 font-display text-2xl font-semibold tracking-tight"
      >
        {t("dashboard.greeting", { name: household.greetingName })}
      </h2>
      <p className="mt-2">
        <span lang="ur" dir="rtl" className="inline-block font-urdu text-xl leading-[2.6]">
          {household.urduTagline}
        </span>
      </p>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
        {t("dashboard.sampleExplanation", { place: household.place, cycle: cycle.label })}
      </p>
      <div className="mt-3">
        <Badge>{t("common.demoData")}</Badge>
      </div>
    </section>
  );
}
