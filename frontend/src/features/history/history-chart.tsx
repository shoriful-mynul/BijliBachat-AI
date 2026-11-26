"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { StoredCycle } from "./store";

/** Bars use kilowatt-hour strings the API already returned. */
export function HistoryChart({
  cycles,
  forecasts,
}: {
  cycles: StoredCycle[];
  forecasts: { cycleId: string; forecast: string; actual: string }[];
}) {
  const points = [...cycles]
    .sort((left, right) => left.ended_at.localeCompare(right.ended_at))
    .map((cycle) => {
      const match = forecasts.find((item) => item.cycleId === cycle.id);
      return {
        id: cycle.id,
        name: cycle.ended_at.slice(0, 10),
        actual: Number(cycle.actual_kwh),
        actualLabel: cycle.actual_kwh,
        forecast: match ? Number(match.forecast) : null,
        forecastLabel: match?.forecast ?? "",
      };
    });

  return (
    <div className="flex flex-col gap-3">
      <div className="h-64 w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 256 }}>
          <BarChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis dataKey="name" tick={{ fill: "var(--muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis width={40} tick={{ fill: "var(--muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--line)",
                borderRadius: 12,
                color: "var(--foreground)",
                fontSize: 14,
              }}
              formatter={(value, name) => {
                const amount = typeof value === "number" ? value : Number(Array.isArray(value) ? value[0] : value ?? 0);
                return [`${amount} kWh`, name === "forecast" ? "Saved forecast" : "Measured use"];
              }}
            />
            <Bar dataKey="actual" name="actual" fill="#42c8e8" radius={[4, 4, 0, 0]} maxBarSize={36} isAnimationActive={false} />
            <Bar dataKey="forecast" name="forecast" fill="#7c8cff" radius={[4, 4, 0, 0]} maxBarSize={36} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Measured cycle consumption, with a saved forecast when one has been compared</caption>
        <thead>
          <tr>
            <th scope="col" className="py-2 font-medium">Cycle end</th>
            <th scope="col" className="py-2 font-medium">Measured kWh</th>
            <th scope="col" className="py-2 font-medium">Saved forecast kWh</th>
          </tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.id} className="border-t border-line">
              <td className="py-2">{point.name}</td>
              <td className="py-2 font-mono">{point.actualLabel}</td>
              <td className="py-2 font-mono">{point.forecastLabel || "Not compared"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
