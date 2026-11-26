"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { getApiBaseUrl } from "@/lib/health";
import { loadCycles } from "./store";
import type { InsightReport } from "./types";

/** Latest measured cycle from this browser. It does not replace the sample cards. */
export function HistorySummary() {
  const apiBase = getApiBaseUrl();
  const [report, setReport] = useState<InsightReport | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const cycles = loadCycles();
    if (!apiBase || cycles.length === 0) {
      queueMicrotask(() => setChecked(true));
      return;
    }
    const controller = new AbortController();
    fetch(`${apiBase}/api/history/insights`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        cycles: cycles.map((cycle) => ({
          id: cycle.id,
          meter_reference: cycle.meter_reference,
          start_checkpoint_id: cycle.start_checkpoint_id,
          end_checkpoint_id: cycle.end_checkpoint_id,
          started_at: cycle.started_at,
          ended_at: cycle.ended_at,
          start_register_kwh: cycle.start_register_kwh,
          end_register_kwh: cycle.end_register_kwh,
        })),
      }),
    })
      .then(async (response) => {
        if (response.ok) {
          setReport((await response.json()) as InsightReport);
        }
      })
      .catch(() => undefined)
      .finally(() => setChecked(true));
    return () => controller.abort();
  }, [apiBase]);

  const trend = report?.direction === "unavailable" ? null : report?.insights[0];

  return (
    <Card as="section" aria-labelledby="history-summary-heading">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="history-summary-heading" className="font-display text-lg font-semibold">
          Measured history
        </h2>
        <DataTrustChip status={report?.latest_cycle_kwh ? "calculated" : "unavailable"} />
      </div>
      {!checked ? (
        <p className="mt-3 text-sm leading-6">Looking for measured cycles on this device.</p>
      ) : report?.latest_cycle_kwh ? (
        <p className="mt-3 text-sm leading-6">
          Latest measured cycle {report.latest_cycle_kwh} kWh
          {report.latest_average_daily_kwh ? `, ${report.latest_average_daily_kwh} kWh on an average day` : ""}.
        </p>
      ) : (
        <p className="mt-3 text-sm leading-6">No measured cycle is saved on this device yet.</p>
      )}
      {trend ? <p className="mt-2 text-sm leading-6">{trend.detail}</p> : null}
      <div className="mt-4">
        <Button href="/history">Open history</Button>
      </div>
    </Card>
  );
}
