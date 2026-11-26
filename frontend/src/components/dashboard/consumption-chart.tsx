"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useI18n } from "@/components/i18n/language-provider";
import { demoDailyUnits } from "@/features/overview/demo-data";

const points = demoDailyUnits.map((point) => ({
  label: point.label,
  units: point.units,
}));

export function ConsumptionChart() {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-3">
      <p className="sr-only">{t("dashboard.chartDescription")}</p>
      <div className="chart-ltr h-56 w-full min-w-0" role="img" aria-label={t("dashboard.chartTitle")}>
        <ResponsiveContainer
          width="100%"
          height="100%"
          initialDimension={{ width: 320, height: 224 }}
        >
          <BarChart
            data={points}
            margin={{ top: 8, right: 4, left: 0, bottom: 0 }}
          >
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis
              dataKey="label"
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={24}
            />
            <YAxis
              width={32}
              allowDecimals={false}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(66, 200, 232, 0.12)" }}
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--line)",
                borderRadius: 12,
                color: "var(--foreground)",
                fontSize: 14,
              }}
              formatter={(value) => {
                const amount = typeof value === "number" ? value : Number(value ?? 0);
                return [t("dashboard.chartDemoTip", { amount }), t("dashboard.chartUse")];
              }}
            />
            <Bar
              dataKey="units"
              name={t("dashboard.chartUse")}
              fill="#42c8e8"
              radius={[4, 4, 0, 0]}
              maxBarSize={16}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-start text-sm">
        <caption className="pb-2 text-start text-sm text-muted">{t("dashboard.chartDescription")}</caption>
        <thead>
          <tr>
            <th scope="col" className="py-2 font-medium">{t("dashboard.chartDay")}</th>
            <th scope="col" className="py-2 font-medium">{t("dashboard.chartKwh")}</th>
          </tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.label}>
              <td>{point.label}</td>
              <td>{point.units}</td>
            </tr>
          ))}
        </tbody>
        </table>
      </div>
    </div>
  );
}
