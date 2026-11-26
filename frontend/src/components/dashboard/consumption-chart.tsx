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
import { demoDailyUnits } from "@/features/overview/demo-data";

const points = demoDailyUnits.map((point) => ({
  label: point.label,
  units: point.units,
}));

export function ConsumptionChart() {
  return (
    <div className="flex flex-col gap-3">
      <div className="h-56 w-full">
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
                return [`${amount} kWh · demo`, "Use"];
              }}
            />
            <Bar
              dataKey="units"
              name="Use"
              fill="#42c8e8"
              radius={[4, 4, 0, 0]}
              maxBarSize={16}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="sr-only">
        <table>
        <caption>Demo daily consumption in kilowatt-hours, 1 to 18 November</caption>
        <thead>
          <tr>
            <th scope="col">Day</th>
            <th scope="col">Kilowatt-hours</th>
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
