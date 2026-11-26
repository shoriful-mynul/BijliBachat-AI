"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useI18n } from "@/components/i18n/language-provider";
import type { ConsumptionReport } from "./types";

/** Bars use API kilowatt-hour strings. The chart does not calculate them. */
export function UsageChart({ lines }: { lines: ConsumptionReport["appliances"] }) {
  const { t } = useI18n();
  const points = lines.map((line) => ({
    name: line.name,
    kwh: Number(line.daily_kwh),
    label: line.daily_kwh,
  }));

  return (
    <div className="flex flex-col gap-3">
      <p className="sr-only">{t("plan.chartDescription")}</p>
      <div className="chart-ltr h-64 w-full min-w-0" role="img" aria-label={t("plan.chartTitle")}>
        <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 256 }}>
          <BarChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis dataKey="name" tick={{ fill: "var(--muted)", fontSize: 12 }} axisLine={false} tickLine={false} interval={0} />
            <YAxis width={40} tick={{ fill: "var(--muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--line)",
                borderRadius: 12,
                color: "var(--foreground)",
                fontSize: 14,
              }}
              formatter={(value) => {
                const amount = typeof value === "number" ? value : Number(Array.isArray(value) ? value[0] : value ?? 0);
                return [`${amount} kWh`, t("plan.chartSeries")];
              }}
            />
            <Bar dataKey="kwh" name={t("plan.chartSeries")} fill="#42c8e8" radius={[4, 4, 0, 0]} maxBarSize={48} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="w-full text-start text-sm">
        <caption className="pb-2 text-start text-sm text-muted">{t("plan.chartCaption")}</caption>
        <thead>
          <tr>
            <th scope="col" className="py-2 font-medium">{t("plan.chartAppliance")}</th>
            <th scope="col" className="py-2 font-medium">{t("plan.chartDaily")}</th>
            <th scope="col" className="py-2 font-medium">{t("plan.chartShare")}</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => (
            <tr key={line.id} className="border-t border-line">
              <td className="py-2"><bdi>{line.name}</bdi></td>
              <td className="py-2 font-mono">{line.daily_kwh}</td>
              <td className="py-2">{line.share_percent ? `${line.share_percent}%` : t("common.unavailable")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
