"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ConsumptionReport } from "./types";

/** Bars use API kilowatt-hour strings. The chart does not calculate them. */
export function UsageChart({ lines }: { lines: ConsumptionReport["appliances"] }) {
  const points = lines.map((line) => ({
    name: line.name,
    kwh: Number(line.daily_kwh),
    label: line.daily_kwh,
  }));

  return (
    <div className="flex flex-col gap-3">
      <div className="h-64 w-full min-w-0">
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
                return [`${amount} kWh`, "Calculated daily use"];
              }}
            />
            <Bar dataKey="kwh" name="Daily use" fill="#42c8e8" radius={[4, 4, 0, 0]} maxBarSize={48} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Calculated daily consumption for each appliance you entered</caption>
        <thead>
          <tr>
            <th scope="col" className="py-2 font-medium">Appliance</th>
            <th scope="col" className="py-2 font-medium">Daily kWh</th>
            <th scope="col" className="py-2 font-medium">Share</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => (
            <tr key={line.id} className="border-t border-line">
              <td className="py-2">{line.name}</td>
              <td className="py-2 font-mono">{line.daily_kwh}</td>
              <td className="py-2">{line.share_percent ? `${line.share_percent}%` : "Unavailable"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
