"use client";

import { useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";
import { LocalizedNotice, SourceText } from "@/components/i18n/source-text";
import { useI18n } from "@/components/i18n/language-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { getApiBaseUrl } from "@/lib/health";
import type { DataTrustStatus } from "@/types/trust";
import { rememberSnapshot } from "@/features/history/store";
import type { ForecastSnapshotResult } from "@/features/history/types";
import { loadReadings, type StoredReading } from "@/features/meter/ledger";
import { ForecastChart } from "./forecast-chart";
import { clearBudget, loadBudget, loadCycle, saveBudget, saveCycle, type StoredBudget, type StoredCycle } from "./stores";
import type { BudgetValidation, ForecastQuantity, ForecastReport } from "./types";

export function PredictionView() {
  const { t } = useI18n();
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
  const [snapshotNote, setSnapshotNote] = useState<string | null>(null);

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
    fetch(`${apiBase}/api/predictions/consumption`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify(forecastPayload(readings, cycle, budget)),
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

  async function saveSnapshot() {
    if (!apiBase || report?.forecast_status !== "estimated") {
      setSnapshotNote("A snapshot is saved only when the forecast is available.");
      return;
    }
    const response = await fetch(`${apiBase}/api/history/forecast-snapshots`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...forecastPayload(readings, cycle, budget), snapshot_id: crypto.randomUUID() }),
    });
    if (!response.ok) {
      setSnapshotNote(await readError(response));
      return;
    }
    const saved = (await response.json()) as ForecastSnapshotResult;
    if (saved.status !== "estimated" || !saved.snapshot) {
      setSnapshotNote(saved.detail);
      return;
    }
    rememberSnapshot(saved.snapshot);
    setSnapshotNote("Saved on this device. The forecast itself was not changed.");
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
        title={t("forecast.introTitle")}
        description={t("forecast.intro")}
      />
      {!apiBase ? <p role="alert">{t("common.apiMissing")}</p> : null}
      {error ? <p role="alert"><LocalizedNotice value={error} /></p> : null}

      <Card as="section" aria-labelledby="forecast-heading">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="forecast-heading" className="font-display text-lg font-semibold">
            {t("forecast.heading")}
          </h2>
          <DataTrustChip status={report?.forecast_status === "estimated" ? "estimated" : "unavailable"} />
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Fact label={t("forecast.used")} quantity={report?.cycle_consumption_kwh} />
          <Fact label={t("forecast.average")} quantity={report?.average_daily_kwh} period={report?.observation_period} />
          <Fact label={t("forecast.additional")} quantity={report?.projected_additional_kwh} />
          <Fact label={t("forecast.cycleEnd")} quantity={report?.projected_cycle_kwh} />
        </div>
        {report?.observation_period ? (
          <p className="mt-3 text-sm leading-6 text-muted">
            {t("forecast.observation", {
              period: report.observation_period,
              days: report.observation_days ? t("forecast.observationDays", { count: report.observation_days }) : "",
              end: report.billing_cycle_ends_on ? t("forecast.cycleEnds", { date: report.billing_cycle_ends_on }) : "",
              remain: report.remaining_days ? t("forecast.daysRemain", { count: report.remaining_days }) : "",
            })}
          </p>
        ) : null}
        {report && report.forecast_status === "unavailable" ? (
          <div className="mt-4">
            <h3 className="text-sm font-semibold">{t("forecast.unavailableTitle")}</h3>
            <ul className="mt-2 flex flex-col gap-1 text-sm leading-6">
              {report.missing_inputs.map((item) => (
                <li key={item}><SourceText>{item}</SourceText></li>
              ))}
            </ul>
          </div>
        ) : null}
        {report && report.series.length > 0 ? (
          <div className="mt-5">
            <ForecastChart series={report.series} />
          </div>
        ) : (
          <p className="mt-4 text-sm leading-6">{t("forecast.noChart")}</p>
        )}
        {report?.forecast_status === "estimated" ? (
          <div className="mt-4">
            <Button type="button" variant="secondary" onClick={() => void saveSnapshot()}>{t("forecast.save")}</Button>
            {snapshotNote ? <p className="mt-2 text-sm leading-6"><LocalizedNotice value={snapshotNote} /></p> : null}
          </div>
        ) : null}
      </Card>

      <Card as="section" aria-labelledby="cycle-heading">
        <h2 id="cycle-heading" className="font-display text-lg font-semibold">
          {t("forecast.cycleTitle")}
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">{t("forecast.cycleHelp")}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <Input label={t("forecast.startDate")} type="date" value={cycle.cycle_started_on} onChange={(event) => setCycle({ ...cycle, cycle_started_on: event.target.value })} />
          <Input label={t("forecast.endDate")} type="date" value={cycle.cycle_ends_on} onChange={(event) => setCycle({ ...cycle, cycle_ends_on: event.target.value })} />
          <Input label={t("forecast.startRegister")} inputMode="decimal" value={cycle.cycle_start_register_kwh} onChange={(event) => setCycle({ ...cycle, cycle_start_register_kwh: event.target.value })} />
          <Select
            label={t("forecast.meter")}
            value={cycle.meter_reference}
            onChange={(event) => setCycle({ ...cycle, meter_reference: event.target.value })}
            options={[{ value: "", label: t("forecast.meterUnknown") }, ...meters.map((item) => ({ value: item, label: item }))]}
          />
          <Input label={t("forecast.company")} value={cycle.provider_code} onChange={(event) => setCycle({ ...cycle, provider_code: event.target.value })} hint={t("forecast.companyHint")} />
          <Select
            label={t("forecast.tariffType")}
            value={cycle.tariff_type}
            onChange={(event) => setCycle({ ...cycle, tariff_type: event.target.value })}
            options={[
              { value: "", label: t("forecast.notSelected") },
              { value: "non_tou", label: t("forecast.nonTou") },
              { value: "tou", label: t("forecast.tou") },
            ]}
          />
          <Select
            label={t("forecast.eligibility")}
            value={cycle.eligibility}
            onChange={(event) => setCycle({ ...cycle, eligibility: event.target.value })}
            options={[
              { value: "", label: t("forecast.notSelected") },
              { value: "lifeline", label: t("forecast.lifeline") },
              { value: "protected", label: t("forecast.protected") },
              { value: "unprotected", label: t("forecast.unprotected") },
            ]}
          />
        </div>
      </Card>

      <Card as="section" aria-labelledby="budget-heading">
        <h2 id="budget-heading" className="font-display text-lg font-semibold">
          {t("forecast.budgetTitle")}
        </h2>
        {budget ? (
          <p className="mt-3 text-sm leading-6">
            {t("forecast.budgetSet", {
              amount: budget.monthly_budget_pkr ? `PKR ${budget.monthly_budget_pkr}` : t("forecast.budgetNotSet"),
              target: budget.monthly_kwh_target ? t("forecast.budgetTarget", { kwh: budget.monthly_kwh_target }) : "",
            })}
          </p>
        ) : (
          <p className="mt-3 text-sm leading-6">{t("forecast.budgetEmpty")}</p>
        )}
        <p className="mt-2 text-sm leading-6 text-muted">{t("forecast.budgetLocal")}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Input label={t("forecast.budgetPkr")} inputMode="decimal" value={budgetPkr} onChange={(event) => setBudgetPkr(event.target.value)} hint={t("forecast.budgetPkrHint")} />
          <Input label={t("forecast.budgetKwh")} inputMode="decimal" value={targetKwh} onChange={(event) => setTargetKwh(event.target.value)} hint={t("forecast.budgetKwhHint")} />
        </div>
        {budgetError ? <p className="mt-3 text-sm" role="alert"><LocalizedNotice value={budgetError} /></p> : null}
        {budgetNote ? <p className="mt-3 text-sm leading-6"><LocalizedNotice value={budgetNote} /></p> : null}
        <div className="mt-4 flex flex-wrap gap-3">
          <Button type="button" onClick={saveBudgetForm}>{t("forecast.saveBudget")}</Button>
          <Button type="button" variant="secondary" onClick={removeBudget}>{t("forecast.clearBudget")}</Button>
        </div>
      </Card>

      <Card as="section" aria-labelledby="compare-heading">
        <h2 id="compare-heading" className="font-display text-lg font-semibold">
          {t("forecast.compareTitle")}
        </h2>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold">{t("forecast.targetTitle")}</h3>
          {report ? <DataTrustChip status={chip(report.target_comparison.trust_status)} /> : null}
        </div>
        <p className="mt-2 text-sm leading-6">{report?.target_comparison.detail ? <SourceText>{report.target_comparison.detail}</SourceText> : t("forecast.targetPending")}</p>
        {report?.target_comparison.direction === "higher" || report?.target_comparison.direction === "lower" || report?.target_comparison.direction === "equal" ? (
          <p className="mt-2 font-mono text-sm">
            {t("forecast.targetLine", {
              projected: report.target_comparison.projected_cycle_kwh ?? "",
              target: report.target_comparison.target_kwh ?? "",
            })}
          </p>
        ) : null}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold">{t("forecast.pkrTitle")}</h3>
          <DataTrustChip status="unavailable" />
        </div>
        <p className="mt-2 text-sm leading-6">{report?.budget_comparison.reason ? <SourceText>{report.budget_comparison.reason}</SourceText> : t("forecast.pkrPending")}</p>
        {report && report.bill_cost.missing_components.length > 0 ? (
          <p className="mt-2 text-sm leading-6 text-muted">{t("common.missing", { items: report.bill_cost.missing_components.join(", ") })}</p>
        ) : null}
        <p className="mt-2 text-sm leading-6"><SourceText>{report?.bill_cost.reason}</SourceText></p>
      </Card>
    </div>
  );
}

function Fact({ label, quantity, period }: { label: string; quantity?: ForecastQuantity; period?: string | null }) {
  const { t } = useI18n();
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold">{label}</h3>
        {quantity ? <DataTrustChip status={chip(quantity.trust_status)} /> : null}
      </div>
      <p className="mt-1 font-mono text-sm">{quantity?.value ?? t("common.unavailable")}</p>
      <p className="mt-1 text-sm leading-6 text-muted"><SourceText>{quantity?.detail}</SourceText></p>
      {period ? <p className="text-sm text-muted">{t("common.period", { period })}</p> : null}
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

function forecastPayload(readings: StoredReading[], cycle: StoredCycle, budget: StoredBudget | null) {
  const selected = readings.filter((item) => (item.meter_reference ?? "") === cycle.meter_reference);
  return {
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
  };
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
