"use client";

import { useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { getApiBaseUrl } from "@/lib/health";
import type { DataTrustStatus } from "@/types/trust";
import { loadReadings, type StoredReading } from "@/features/meter/ledger";
import { ForecastChart } from "./forecast-chart";
import { clearBudget, loadBudget, loadCycle, saveBudget, saveCycle, type StoredBudget, type StoredCycle } from "./stores";
import type { BudgetValidation, ForecastQuantity, ForecastReport } from "./types";

export function PredictionView() {
  const apiBase = getApiBaseUrl();
  const [ready, setReady] = useState(false);
  const [readings, setReadings] = useState<StoredReading[]>([]);
  const [cycle, setCycle] = useState<StoredCycle>(loadCycleFallback());
  const [budget, setBudget] = useState<StoredBudget | null>(null);
  const [budgetPkr, setBudgetPkr] = useState("");
  const [targetKwh, setTargetKwh] = useState("");
  const [budgetError, setBudgetError] = useState<string | null>(null);
  const [budgetNote, setBudgetNote] = useState<string | null>(null);
  const [report, setReport] = useState<ForecastReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedReadings = loadReadings();
    const storedBudget = loadBudget();
    const storedCycle = loadCycle();
    queueMicrotask(() => {
      setReadings(storedReadings);
      setBudget(storedBudget);
      setCycle(storedCycle);
      setBudgetPkr(storedBudget?.monthly_budget_pkr ?? "");
      setTargetKwh(storedBudget?.monthly_kwh_target ?? "");
      setReady(true);
    });
  }, []);

  useEffect(() => {
    if (!ready) {
      return;
    }
    saveCycle(cycle);
  }, [ready, cycle]);

  useEffect(() => {
    if (!ready || !apiBase) {
      return;
    }
    const controller = new AbortController();
    const selected = readings.filter((item) => (item.meter_reference ?? "") === cycle.meter_reference);
    fetch(`${apiBase}/api/predictions/consumption`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        as_of: new Date().toISOString(),
        meter_reference: cycle.meter_reference || null,
        readings: selected.map(toPrior),
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
        if (!response.ok) {
          setError(await readError(response));
          setReport(null);
          return;
        }
        setReport((await response.json()) as ForecastReport);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (!(cause instanceof DOMException && cause.name === "AbortError")) {
          setError("The forecast could not be calculated.");
        }
      });
    return () => controller.abort();
  }, [apiBase, ready, readings, cycle, budget]);

  async function saveBudgetForm() {
    if (!apiBase) {
      return;
    }
    setBudgetError(null);
    const response = await fetch(`${apiBase}/api/predictions/budget`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        monthly_budget_pkr: budgetPkr.trim() || null,
        monthly_kwh_target: targetKwh.trim() || null,
      }),
    });
    if (!response.ok) {
      setBudgetError(await readError(response));
      return;
    }
    const validated = (await response.json()) as BudgetValidation;
    const next = {
      monthly_budget_pkr: validated.monthly_budget_pkr,
      monthly_kwh_target: validated.monthly_kwh_target,
    };
    saveBudget(next);
    setBudget(next);
    setBudgetNote(validated.limitation);
  }

  function removeBudget() {
    clearBudget();
    setBudget(null);
    setBudgetPkr("");
    setTargetKwh("");
    setBudgetError(null);
    setBudgetNote("The budget was cleared from this browser.");
  }

  const meters = Array.from(
    new Set(readings.map((item) => item.meter_reference).filter((item): item is string => Boolean(item))),
  );

  return (
    <div className="flex flex-col gap-5">
      <EmptyState
        icon={TrendingUp}
        title="An estimate from the pace of your checkpoints"
        description="This uses readings kept on this device. It is not a confirmed bill, and it does not watch the meter continuously. A future unit figure is an estimate. A rupee total is shown only when a complete tariff can price it."
      />
      {!apiBase ? <p role="alert">The API address is not configured.</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <Card as="section" aria-labelledby="forecast-heading">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="forecast-heading" className="font-display text-lg font-semibold">
            Consumption forecast
          </h2>
          <DataTrustChip status={report?.forecast_status === "estimated" ? "estimated" : "unavailable"} />
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Fact label="Used so far this cycle" quantity={report?.cycle_consumption_kwh} />
          <Fact label="Observed average per day" quantity={report?.average_daily_kwh} period={report?.observation_period} />
          <Fact label="Estimated additional use" quantity={report?.projected_additional_kwh} />
          <Fact label="Estimated use by the cycle end" quantity={report?.projected_cycle_kwh} />
        </div>
        {report?.observation_period ? (
          <p className="mt-3 text-sm leading-6 text-muted">
            Observation period {report.observation_period}
            {report.observation_days ? ` (${report.observation_days} days)` : ""}.
            {report.billing_cycle_ends_on ? ` Billing cycle ends ${report.billing_cycle_ends_on}.` : ""}
            {report.remaining_days ? ` ${report.remaining_days} days remain.` : ""}
          </p>
        ) : null}
        {report && report.forecast_status === "unavailable" ? (
          <div className="mt-4">
            <h3 className="text-sm font-semibold">The forecast is not available yet</h3>
            <ul className="mt-2 flex flex-col gap-1 text-sm leading-6">
              {report.missing_inputs.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {report && report.series.length > 0 ? (
          <div className="mt-5">
            <ForecastChart series={report.series} />
          </div>
        ) : (
          <p className="mt-4 text-sm leading-6">No chart is shown until a forecast can be calculated from real checkpoints. Missing days are not filled in.</p>
        )}
      </Card>

      <Card as="section" aria-labelledby="cycle-heading">
        <h2 id="cycle-heading" className="font-display text-lg font-semibold">
          Billing cycle
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Enter the cycle dates and the register at the start of the cycle. These stay in this browser, separate from the meter checkpoints. An older checkpoint is not treated as the cycle start.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <Input label="Cycle start date" type="date" value={cycle.cycle_started_on} onChange={(event) => setCycle({ ...cycle, cycle_started_on: event.target.value })} />
          <Input label="Cycle end date" type="date" value={cycle.cycle_ends_on} onChange={(event) => setCycle({ ...cycle, cycle_ends_on: event.target.value })} />
          <Input label="Register at cycle start" inputMode="decimal" value={cycle.cycle_start_register_kwh} onChange={(event) => setCycle({ ...cycle, cycle_start_register_kwh: event.target.value })} />
          <Select
            label="Meter"
            value={cycle.meter_reference}
            onChange={(event) => setCycle({ ...cycle, meter_reference: event.target.value })}
            options={[{ value: "", label: "Meter number not recorded" }, ...meters.map((item) => ({ value: item, label: item }))]}
          />
          <Input label="Distribution company" value={cycle.provider_code} onChange={(event) => setCycle({ ...cycle, provider_code: event.target.value })} hint="Optional. Used only to look for a complete payable tariff." />
          <Select
            label="Tariff type"
            value={cycle.tariff_type}
            onChange={(event) => setCycle({ ...cycle, tariff_type: event.target.value })}
            options={[
              { value: "", label: "Not selected" },
              { value: "non_tou", label: "Non time-of-use" },
              { value: "tou", label: "Time of use" },
            ]}
          />
          <Select
            label="Eligibility you can confirm"
            value={cycle.eligibility}
            onChange={(event) => setCycle({ ...cycle, eligibility: event.target.value })}
            options={[
              { value: "", label: "Not selected" },
              { value: "lifeline", label: "Lifeline" },
              { value: "protected", label: "Protected" },
              { value: "unprotected", label: "Unprotected" },
            ]}
          />
        </div>
      </Card>

      <Card as="section" aria-labelledby="budget-heading">
        <h2 id="budget-heading" className="font-display text-lg font-semibold">
          Your budget
        </h2>
        {budget ? (
          <p className="mt-3 text-sm leading-6">
            Monthly budget {budget.monthly_budget_pkr ? `PKR ${budget.monthly_budget_pkr}` : "not set"}.
            {budget.monthly_kwh_target ? ` Consumption target ${budget.monthly_kwh_target} kWh.` : ""}
            {" "}This is a figure you entered. It is not a tariff.
          </p>
        ) : (
          <p className="mt-3 text-sm leading-6">No budget is saved in this browser yet. Add one if you want a target to compare later.</p>
        )}
        <p className="mt-2 text-sm leading-6 text-muted">Saved only in this browser. It is not synchronized to another device, and it is stored apart from meter readings.</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Input label="Monthly budget (PKR)" inputMode="decimal" value={budgetPkr} onChange={(event) => setBudgetPkr(event.target.value)} hint="Greater than zero and up to 1000000.00." />
          <Input label="Monthly use target (kWh)" inputMode="decimal" value={targetKwh} onChange={(event) => setTargetKwh(event.target.value)} hint="Optional household preference. Not a tariff limit." />
        </div>
        {budgetError ? <p className="mt-3 text-sm" role="alert">{budgetError}</p> : null}
        {budgetNote ? <p className="mt-3 text-sm leading-6">{budgetNote}</p> : null}
        <div className="mt-4 flex flex-wrap gap-3">
          <Button type="button" onClick={saveBudgetForm}>Save budget on this device</Button>
          <Button type="button" variant="secondary" onClick={removeBudget}>Clear budget</Button>
        </div>
      </Card>

      <Card as="section" aria-labelledby="compare-heading">
        <h2 id="compare-heading" className="font-display text-lg font-semibold">
          Comparison
        </h2>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold">Consumption target</h3>
          {report ? <DataTrustChip status={chip(report.target_comparison.trust_status)} /> : null}
        </div>
        <p className="mt-2 text-sm leading-6">{report?.target_comparison.detail ?? "The comparison appears after the forecast is calculated."}</p>
        {report?.target_comparison.direction === "higher" || report?.target_comparison.direction === "lower" || report?.target_comparison.direction === "equal" ? (
          <p className="mt-2 font-mono text-sm">
            Estimated {report.target_comparison.projected_cycle_kwh} kWh, target {report.target_comparison.target_kwh} kWh.
          </p>
        ) : null}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold">PKR budget</h3>
          <DataTrustChip status="unavailable" />
        </div>
        <p className="mt-2 text-sm leading-6">{report?.budget_comparison.reason ?? "A payable amount is not available, so the budget cannot be compared."}</p>
        {report && report.bill_cost.missing_components.length > 0 ? (
          <p className="mt-2 text-sm leading-6 text-muted">Missing: {report.bill_cost.missing_components.join(", ")}.</p>
        ) : null}
        <p className="mt-2 text-sm leading-6">{report?.bill_cost.reason}</p>
      </Card>
    </div>
  );
}

function Fact({ label, quantity, period }: { label: string; quantity?: ForecastQuantity; period?: string | null }) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold">{label}</h3>
        {quantity ? <DataTrustChip status={chip(quantity.trust_status)} /> : null}
      </div>
      <p className="mt-1 font-mono text-sm">{quantity?.value ?? "Unavailable"}</p>
      <p className="mt-1 text-sm leading-6 text-muted">{quantity?.detail}</p>
      {period ? <p className="text-sm text-muted">Period {period}.</p> : null}
    </div>
  );
}

function chip(status: string): DataTrustStatus {
  const key = status.toLowerCase();
  if (key === "verified" || key === "calculated" || key === "extracted" || key === "estimated" || key === "unavailable") {
    return key;
  }
  return "unavailable";
}

function toPrior(reading: StoredReading) {
  return {
    id: reading.id,
    register_kwh: reading.register_kwh,
    read_at: reading.read_at,
    meter_reference: reading.meter_reference,
    capture_method: reading.capture_method,
    trust_status: reading.trust_status,
  };
}

function loadCycleFallback() {
  return {
    cycle_started_on: "",
    cycle_ends_on: "",
    cycle_start_register_kwh: "",
    meter_reference: "",
    provider_code: "",
    tariff_type: "",
    eligibility: "",
  };
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { message?: string; detail?: { msg?: string }[] };
    if (typeof body.message === "string" && body.message.trim()) {
      return body.message;
    }
    const first = body.detail?.[0]?.msg;
    if (typeof first === "string" && first.trim()) {
      return first;
    }
  } catch {
    return "The request could not be completed.";
  }
  return "Check the values and try again.";
}
