"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { getApiBaseUrl } from "@/lib/health";
import { loadReadings } from "@/features/meter/ledger";
import { loadBudget, loadCycle } from "./stores";
import type { ForecastReport } from "./types";

/** A short forecast from the same API and the same device-local checkpoints. */
export function PredictionSummary() {
  const apiBase = getApiBaseUrl();
  const [report, setReport] = useState<ForecastReport | null>(null);

  useEffect(() => {
    if (!apiBase) {
      return;
    }
    const readings = loadReadings();
    const cycle = loadCycle();
    const budget = loadBudget();
    const selected = readings.filter((item) => (item.meter_reference ?? "") === cycle.meter_reference);
    const controller = new AbortController();
    fetch(`${apiBase}/api/predictions/consumption`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        as_of: new Date().toISOString(),
        meter_reference: cycle.meter_reference || null,
        readings: selected.map((item) => ({
          id: item.id,
          register_kwh: item.register_kwh,
          read_at: item.read_at,
          meter_reference: item.meter_reference,
          capture_method: item.capture_method,
          trust_status: item.trust_status,
        })),
        cycle_started_on: cycle.cycle_started_on || null,
        cycle_ends_on: cycle.cycle_ends_on || null,
        cycle_start_register_kwh: cycle.cycle_start_register_kwh.trim() || null,
        monthly_budget_pkr: budget?.monthly_budget_pkr ?? null,
        monthly_kwh_target: budget?.monthly_kwh_target ?? null,
        provider_code: cycle.provider_code.trim() || null,
        consumer_category: cycle.provider_code.trim() ? "residential" : null,
        tariff_type: cycle.tariff_type || null,
        eligibility: cycle.eligibility || null,
        billing_date: cycle.provider_code.trim() && cycle.tariff_type ? new Date().toISOString().slice(0, 10) : null,
      }),
    })
      .then(async (response) => {
        if (response.ok) {
          setReport((await response.json()) as ForecastReport);
        }
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [apiBase]);

  const estimated = report?.forecast_status === "estimated" && report.projected_cycle_kwh.value;

  return (
    <Card as="section" aria-labelledby="prediction-summary-heading">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="prediction-summary-heading" className="font-display text-lg font-semibold">
          Forecast from your checkpoints
        </h2>
        <DataTrustChip status={estimated ? "estimated" : "unavailable"} />
      </div>
      {estimated ? (
        <p className="mt-3 text-sm leading-6">
          If the observed pace continues, estimated use by the cycle end is {report?.projected_cycle_kwh.value} kWh.
          This is not a meter reading and not a confirmed bill.
        </p>
      ) : (
        <p className="mt-3 text-sm leading-6">
          {report?.missing_inputs[0] ?? "Add checkpoints and the billing-cycle register before a forecast can be shown."}
        </p>
      )}
      <p className="mt-2 text-sm leading-6 text-muted">
        {report?.budget_comparison.reason ?? "A payable rupee forecast is not available from the loaded tariff files."}
      </p>
      <div className="mt-4">
        <Button href="/prediction">Open the forecast</Button>
      </div>
    </Card>
  );
}
