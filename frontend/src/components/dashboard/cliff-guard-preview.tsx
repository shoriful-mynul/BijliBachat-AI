"use client";

import { useI18n } from "@/components/i18n/language-provider";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { RiskIndicator } from "@/components/ui/risk-indicator";
import { SectionHeader } from "@/components/ui/section-header";

export function CliffGuardPreview() {
  const { t } = useI18n();
  return (
    <Card className="h-full">
      <SectionHeader title={t("dashboard.cliffTitle")} description={t("dashboard.cliffDescription")} />
      <div className="mt-5 flex items-center gap-4">
        <svg
          viewBox="0 0 120 120"
          className="h-28 w-28 shrink-0 text-raised"
          aria-hidden="true"
        >
          <circle
            cx="60"
            cy="60"
            r="46"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeDasharray="4 8"
          />
          <text
            x="60"
            y="66"
            textAnchor="middle"
            fill="var(--foreground)"
            fontSize="22"
            fontFamily="var(--font-mono), ui-monospace, monospace"
          >
            —
          </text>
        </svg>
        <div className="min-w-0">
          <p className="text-sm font-medium">{t("dashboard.noThreshold")}</p>
          <p className="mt-1 text-sm leading-6 text-muted">{t("dashboard.noThresholdDetail")}</p>
        </div>
      </div>
      <div className="mt-5 flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted">{t("dashboard.tariffData")}</span>
          <DataTrustChip status="unavailable" />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted">{t("dashboard.riskStatus")}</span>
          <RiskIndicator level="needs-verification" />
        </div>
      </div>
      <p className="mt-4 text-sm leading-6 text-muted">{t("dashboard.protectedNote")}</p>
    </Card>
  );
}
