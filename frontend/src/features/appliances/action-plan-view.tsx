"use client";

import { useEffect, useState } from "react";
import { ListChecks } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { getApiBaseUrl } from "@/lib/health";
import type { DataTrustStatus } from "@/types/trust";
import { UsageChart } from "./usage-chart";
import {
  loadAppliances,
  loadScenario,
  saveAppliances,
  saveScenario,
  type ScenarioDraft,
  type StoredAppliance,
} from "./store";
import type { ActionPlanReport, ConsumptionReport, ScenarioReport } from "./types";

type Draft = {
  id: string | null;
  name: string;
  category: string;
  watts: string;
  quantity: string;
  hours: string;
  daysPerWeek: string;
  notes: string;
};

const blankDraft: Draft = {
  id: null,
  name: "",
  category: "",
  watts: "",
  quantity: "1",
  hours: "",
  daysPerWeek: "",
  notes: "",
};

export function ActionPlanView() {
  const apiBase = getApiBaseUrl();
  const [ready, setReady] = useState(false);
  const [appliances, setAppliances] = useState<StoredAppliance[]>([]);
  const [scenario, setScenario] = useState<ScenarioDraft>({ days: "", changes: {} });
  const [draft, setDraft] = useState<Draft>(blankDraft);
  const [formError, setFormError] = useState<string | null>(null);
  const [consumption, setConsumption] = useState<ConsumptionReport | null>(null);
  const [comparison, setComparison] = useState<ScenarioReport | null>(null);
  const [plan, setPlan] = useState<ActionPlanReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedAppliances = loadAppliances();
    const storedScenario = loadScenario();
    queueMicrotask(() => {
      setAppliances(storedAppliances);
      setScenario(storedScenario);
      setReady(true);
    });
  }, []);

  useEffect(() => {
    if (!ready) {
      return;
    }
    saveAppliances(appliances);
    saveScenario(scenario);
  }, [ready, appliances, scenario]);

  useEffect(() => {
    if (!ready || !apiBase) {
      return;
    }
    const controller = new AbortController();
    const days = wholeDays(scenario.days);
    const baseline = appliances.map((item) => toSpec(item));
    const proposed = appliances.map((item) => toSpec(item, scenario.changes[item.id]));
    const consumptionBody = { appliances: baseline, days };
    fetch(`${apiBase}/api/appliances/consumption`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify(consumptionBody),
    })
      .then(async (response) => {
        if (!response.ok) {
          setError(await readError(response));
          setConsumption(null);
          return;
        }
        setConsumption((await response.json()) as ConsumptionReport);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (!(cause instanceof DOMException && cause.name === "AbortError")) {
          setError("Appliance use could not be calculated.");
        }
      });
    if (days === undefined) {
      queueMicrotask(() => {
        setComparison(null);
        setPlan(null);
      });
      return () => controller.abort();
    }
    const scenarioBody = { baseline, proposed, days };
    void postJson<ScenarioReport>(`${apiBase}/api/appliances/scenarios`, scenarioBody, controller.signal).then((result) => {
      if (result.ok) {
        setComparison(result.body);
      } else if (result.message) {
        setError(result.message);
        setComparison(null);
      }
    });
    void postJson<ActionPlanReport>(`${apiBase}/api/appliances/action-plan`, scenarioBody, controller.signal).then((result) => {
      if (result.ok) {
        setPlan(result.body);
      } else if (result.message) {
        setPlan(null);
      }
    });
    return () => controller.abort();
  }, [apiBase, ready, appliances, scenario]);

  function saveDraft() {
    const problem = validateDraft(draft);
    if (problem) {
      setFormError(problem);
      return;
    }
    const next: StoredAppliance = {
      id: draft.id ?? crypto.randomUUID(),
      name: draft.name.trim(),
      category: draft.category.trim() || null,
      rated_watts: draft.watts.trim(),
      quantity: Number(draft.quantity),
      operating_hours_per_day: draft.hours.trim(),
      operating_days_per_week: draft.daysPerWeek.trim() ? Number(draft.daysPerWeek) : null,
      notes: draft.notes.trim() || null,
    };
    setAppliances((current) => {
      const exists = current.some((item) => item.id === next.id);
      return exists ? current.map((item) => (item.id === next.id ? next : item)) : [...current, next];
    });
    setDraft(blankDraft);
    setFormError(null);
  }

  function removeAppliance(id: string) {
    setAppliances((current) => current.filter((item) => item.id !== id));
    setScenario((current) => {
      const changes = { ...current.changes };
      delete changes[id];
      return { ...current, changes };
    });
  }

  function updateChange(id: string, patch: Partial<ScenarioDraft["changes"][string]>, appliance: StoredAppliance) {
    setScenario((current) => {
      const existing = current.changes[id] ?? {
        operating_hours_per_day: appliance.operating_hours_per_day,
        quantity: appliance.quantity,
        operating_days_per_week: appliance.operating_days_per_week,
      };
      return { ...current, changes: { ...current.changes, [id]: { ...existing, ...patch } } };
    });
  }

  const pkr = plan?.pkr_impact ?? comparison?.pkr_impact ?? consumption?.pkr_impact;

  return (
    <div className="flex flex-col gap-5">
      <EmptyState
        icon={ListChecks}
        title="See what a different schedule would use"
        description="Enter the appliances you actually use. The figures are calculated from those entries. A scenario is not a measured saving, and a rupee amount is not shown."
      />
      {!apiBase ? <p role="alert">The API address is not configured.</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <Card as="section" aria-labelledby="inventory-heading">
        <h2 id="inventory-heading" className="font-display text-lg font-semibold">
          Appliances in this home
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Saved only in this browser. Another device cannot see this list. Wattage is what you enter, not a verified rating.
        </p>
        {appliances.length === 0 ? (
          <p className="mt-4 text-sm leading-6">No appliances yet. Add the first one with its power and the hours you usually run it.</p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {appliances.map((item) => {
              const line = consumption?.appliances.find((entry) => entry.id === item.id);
              return (
                <li key={item.id} className="rounded-xl border border-line p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-semibold">{item.name}</h3>
                    {line ? <DataTrustChip status="calculated" /> : null}
                  </div>
                  <p className="mt-2 text-sm leading-6">
                    {item.quantity} × {item.rated_watts} W, {item.operating_hours_per_day} hours a day
                    {item.operating_days_per_week ? `, ${item.operating_days_per_week} days a week` : ", every day of the period"}.
                  </p>
                  <p className="mt-1 font-mono text-sm">{line ? `${line.daily_kwh} kWh on an average day` : "Waiting for the calculation."}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button type="button" variant="secondary" onClick={() => setDraft(fromAppliance(item))}>Edit</Button>
                    <Button type="button" variant="ghost" onClick={() => removeAppliance(item.id)}>Delete</Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <Input label="Appliance name" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
          <Input label="Category" value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })} hint="Optional. For example cooling or laundry." />
          <Input label="Power (watts)" inputMode="decimal" value={draft.watts} onChange={(event) => setDraft({ ...draft, watts: event.target.value })} />
          <Input label="How many" inputMode="numeric" value={draft.quantity} onChange={(event) => setDraft({ ...draft, quantity: event.target.value })} />
          <Input label="Hours on a day it runs" inputMode="decimal" value={draft.hours} onChange={(event) => setDraft({ ...draft, hours: event.target.value })} hint="More than 0 and at most 24." />
          <Input label="Days each week" inputMode="numeric" value={draft.daysPerWeek} onChange={(event) => setDraft({ ...draft, daysPerWeek: event.target.value })} hint="Optional. Leave blank to count every day." />
          <Input label="Notes" value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} />
        </div>
        {formError ? <p className="mt-3 text-sm" role="alert">{formError}</p> : null}
        <div className="mt-4">
          <Button type="button" onClick={saveDraft}>{draft.id ? "Save changes" : "Add appliance"}</Button>
        </div>
      </Card>

      <Card as="section" aria-labelledby="overview-heading">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="overview-heading" className="font-display text-lg font-semibold">
            Calculated use
          </h2>
          <DataTrustChip status={consumption?.status === "calculated" ? "calculated" : "unavailable"} />
        </div>
        {consumption?.status === "calculated" ? (
          <>
            <p className="mt-3 font-mono text-sm">
              {consumption.total_daily_kwh} kWh on an average day
              {consumption.total_period_kwh ? `. ${consumption.total_period_kwh} kWh over ${consumption.days} days` : ""}.
            </p>
            <div className="mt-4">
              <UsageChart lines={consumption.appliances} />
            </div>
          </>
        ) : (
          <p className="mt-3 text-sm leading-6">Add an appliance before a consumption chart can be shown. No sample appliances are included.</p>
        )}
        <div className="mt-4 max-w-xs">
          <Input
            label="Days to compare"
            inputMode="numeric"
            value={scenario.days}
            onChange={(event) => setScenario({ ...scenario, days: event.target.value })}
            hint="From 1 to 366. A 30-day month is not assumed."
          />
        </div>
      </Card>

      <Card as="section" aria-labelledby="scenario-heading">
        <h2 id="scenario-heading" className="font-display text-lg font-semibold">
          Try a different schedule
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          These fields do not change the appliances you saved. Reset returns the proposal to that saved schedule.
        </p>
        {appliances.length === 0 ? <p className="mt-4 text-sm">Add an appliance before trying a schedule.</p> : null}
        <div className="mt-4 flex flex-col gap-4">
          {appliances.map((item) => {
            const change = scenario.changes[item.id];
            return (
              <div key={item.id} className="grid gap-3 md:grid-cols-3">
                <p className="text-sm font-semibold md:col-span-3">{item.name}</p>
                <Input
                  label="Proposed hours"
                  inputMode="decimal"
                  value={change?.operating_hours_per_day ?? item.operating_hours_per_day}
                  onChange={(event) => updateChange(item.id, { operating_hours_per_day: event.target.value }, item)}
                />
                <Input
                  label="Proposed quantity"
                  inputMode="numeric"
                  value={String(change?.quantity ?? item.quantity)}
                  onChange={(event) => updateChange(item.id, { quantity: Number(event.target.value) }, item)}
                />
                <Input
                  label="Proposed days each week"
                  inputMode="numeric"
                  value={String(change?.operating_days_per_week ?? item.operating_days_per_week ?? "")}
                  onChange={(event) =>
                    updateChange(
                      item.id,
                      { operating_days_per_week: event.target.value.trim() ? Number(event.target.value) : null },
                      item,
                    )
                  }
                />
              </div>
            );
          })}
        </div>
        <div className="mt-4">
          <Button type="button" variant="secondary" onClick={() => setScenario({ ...scenario, changes: {} })}>
            Reset scenario
          </Button>
        </div>
        {comparison?.status === "estimated" ? (
          <div className="mt-4">
            <DataTrustChip status="estimated" />
            <p className="mt-2 text-sm leading-6">
              Current schedule {comparison.baseline_kwh} kWh. Proposed schedule {comparison.scenario_kwh} kWh.
              {" "}
              {comparison.direction === "reduced"
                ? `That is ${comparison.difference_kwh} kWh less`
                : comparison.direction === "increased"
                  ? `That is ${comparison.difference_kwh} kWh more`
                  : "There is no difference"}
              {comparison.percentage_difference ? ` (${comparison.percentage_difference}%)` : ""}.
            </p>
          </div>
        ) : (
          <p className="mt-4 text-sm leading-6">Enter the number of days before the comparison can be calculated.</p>
        )}
      </Card>

      <Card as="section" aria-labelledby="actions-heading">
        <h2 id="actions-heading" className="font-display text-lg font-semibold">
          Actions from this scenario
        </h2>
        {plan && plan.actions.length > 0 ? (
          <ul className="mt-4 flex flex-col gap-3">
            {plan.actions.map((action) => (
              <li key={action.appliance_id} className="rounded-xl border border-line p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">{action.title}</h3>
                  <DataTrustChip status={chip(action.trust_status)} />
                </div>
                <p className="mt-2 text-sm leading-6">Current: {action.baseline_assumption}</p>
                <p className="mt-1 text-sm leading-6">Proposed: {action.proposed_assumption}</p>
                <p className="mt-2 font-mono text-sm">
                  {action.direction === "reduced" ? `${action.difference_kwh} kWh less` : `${action.difference_kwh} kWh more`}
                </p>
                <p className="mt-2 text-sm leading-6">{action.explanation}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm leading-6">{plan?.detail ?? "Change a proposed hour or quantity, and enter the number of days, before an action can show a difference."}</p>
        )}
      </Card>

      <Card as="section" aria-labelledby="pkr-heading">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="pkr-heading" className="font-display text-lg font-semibold">
            Rupee savings
          </h2>
          <DataTrustChip status="unavailable" />
        </div>
        <p className="mt-3 text-sm leading-6">
          {pkr?.reason ?? "PKR savings are unavailable until a complete payable tariff can price both schedules. No electricity rate is assumed."}
        </p>
        {pkr && pkr.missing_components.length > 0 ? (
          <p className="mt-2 text-sm leading-6 text-muted">Missing from the loaded tariffs: {pkr.missing_components.join(", ")}.</p>
        ) : null}
      </Card>
    </div>
  );
}

function fromAppliance(item: StoredAppliance): Draft {
  return {
    id: item.id,
    name: item.name,
    category: item.category ?? "",
    watts: item.rated_watts,
    quantity: String(item.quantity),
    hours: item.operating_hours_per_day,
    daysPerWeek: item.operating_days_per_week ? String(item.operating_days_per_week) : "",
    notes: item.notes ?? "",
  };
}

function toSpec(item: StoredAppliance, change?: ScenarioDraft["changes"][string]) {
  return {
    id: item.id,
    name: item.name,
    category: item.category,
    rated_watts: item.rated_watts,
    quantity: change?.quantity ?? item.quantity,
    operating_hours_per_day: change?.operating_hours_per_day ?? item.operating_hours_per_day,
    operating_days_per_week: change ? change.operating_days_per_week : item.operating_days_per_week,
    notes: item.notes,
  };
}

function wholeDays(value: string): number | undefined {
  if (!/^[1-9][0-9]*$/.test(value.trim())) {
    return undefined;
  }
  const days = Number(value);
  if (days < 1 || days > 366) {
    return undefined;
  }
  return days;
}

function validateDraft(draft: Draft): string | null {
  if (!draft.name.trim()) {
    return "Enter a name.";
  }
  if (!/^\d+(\.\d+)?$/.test(draft.watts.trim()) || Number(draft.watts) <= 0) {
    return "Enter a power rating greater than zero.";
  }
  if (!/^[1-9][0-9]*$/.test(draft.quantity.trim()) || Number(draft.quantity) > 100) {
    return "Enter a quantity from 1 to 100.";
  }
  if (!/^\d+(\.\d+)?$/.test(draft.hours.trim())) {
    return "Enter the hours as a plain number.";
  }
  const hours = Number(draft.hours);
  if (hours <= 0 || hours > 24) {
    return "Hours must be more than 0 and no more than 24.";
  }
  if (draft.daysPerWeek.trim()) {
    const days = Number(draft.daysPerWeek);
    if (!/^[1-7]$/.test(draft.daysPerWeek.trim()) || days < 1 || days > 7) {
      return "Days each week must be from 1 to 7, or blank.";
    }
  }
  return null;
}

function chip(status: string): DataTrustStatus {
  const key = status.toLowerCase();
  if (key === "verified" || key === "calculated" || key === "extracted" || key === "estimated" || key === "unavailable") {
    return key;
  }
  return "unavailable";
}

async function postJson<T>(
  url: string,
  body: unknown,
  signal: AbortSignal,
): Promise<{ ok: true; body: T } | { ok: false; message?: string }> {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      return { ok: false, message: await readError(response) };
    }
    return { ok: true, body: (await response.json()) as T };
  } catch {
    return { ok: false };
  }
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { message?: string; detail?: { msg?: string }[] };
    if (typeof body.message === "string" && body.message.trim()) {
      return body.message;
    }
    const first = body.detail?.[0]?.msg;
    if (typeof first === "string") {
      return first;
    }
  } catch {
    return "The request could not be completed.";
  }
  return "Check the appliance details and try again.";
}
