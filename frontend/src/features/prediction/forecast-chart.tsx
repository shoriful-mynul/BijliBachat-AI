"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ForecastReport } from "./types";

type ForecastChartProps = {
  series: ForecastReport["series"];
};

/** Observed checkpoints and one estimated point at the cycle end. No days are filled in. */
export function ForecastChart({ series }: ForecastChartProps) {
  const lastObserved = [...series].reverse().find((point) => point.kind === "observed");
  const points = series.map((point) => ({
    label: point.label,
    observed: point.kind === "observed" ? Number(point.kwh) : null,
    estimated:
      point.kind === "estimated" || (lastObserved && point.label === lastObserved.label)
        ? Number(point.kwh)
        : null,
  }));

  return (
    <div className="flex flex-col gap-3">
      <div className="h-64 w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 256 }}>
          <LineChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis dataKey="label" tick={{ fill: "var(--muted)", fontSize: 12 }} axisLine={false} tickLine={false} interval="preserveStartEnd" minTickGap={24} />
            <YAxis width={40} tick={{ fill: "var(--muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--line)",
                borderRadius: 12,
                color: "var(--foreground)",
                fontSize: 14,
              }}
            />
            <Legend />
            <Line type="monotone" dataKey="observed" name="Observed kWh" stroke="#42c8e8" strokeWidth={2} dot connectNulls={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="estimated" name="Estimated kWh" stroke="#e2a33a" strokeWidth={2} strokeDasharray="5 4" dot connectNulls={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Observed cycle consumption and the estimated point at the billing-cycle end</caption>
        <thead>
          <tr>
            <th scope="col" className="py-2 font-medium">Point</th>
            <th scope="col" className="py-2 font-medium">kWh since cycle start</th>
            <th scope="col" className="py-2 font-medium">Kind</th>
          </tr>
        </thead>
        <tbody>
          {series.map((point) => (
            <tr key={`${point.kind}-${point.label}`} className="border-t border-line">
              <td className="py-2">{point.label}</td>
              <td className="py-2 font-mono">{point.kwh}</td>
              <td className="py-2">{point.kind === "observed" ? "Observed" : "Estimated"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
