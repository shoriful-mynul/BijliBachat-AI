"use client";

import { useEffect, useState } from "react";
import { History } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { getApiBaseUrl } from "@/lib/health";
import type { DataTrustStatus } from "@/types/trust";
import { loadReadings, type StoredReading } from "@/features/meter/ledger";
import { HistoryChart } from "./history-chart";
import {
  loadBaselines,
  loadCycles,
  loadSnapshots,
  saveBaselines,
  saveCycles,
  type StoredBaseline,
  type StoredCycle,
  type StoredSnapshot,
} from "./store";
import type { BaselineComparison, CycleComparison, CycleValidation, ForecastComparison, InsightReport } from "./types";

export function HistoryView() {
  const apiBase = getApiBaseUrl();
  const [ready, setReady] = useState(false);
  const [readings, setReadings] = useState<StoredReading[]>([]);
  const [cycles, setCycles] = useState<StoredCycle[]>([]);
  const [snapshots, setSnapshots] = useState<StoredSnapshot[]>([]);
  const [baselines, setBaselines] = useState<StoredBaseline[]>([]);
  const [startId, setStartId] = useState("");
  const [endId, setEndId] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const [earlierId, setEarlierId] = useState("");
  const [laterId, setLaterId] = useState("");
  const [comparison, setComparison] = useState<CycleComparison | null>(null);
  const [forecastResult, setForecastResult] = useState<ForecastComparison | null>(null);
  const [forecastMatches, setForecastMatches] = useState<{ cycleId: string; forecast: string; actual: string }[]>([]);
  const [baselineResults, setBaselineResults] = useState<Record<string, BaselineComparison>>({});
  const [targetDrafts, setTargetDrafts] = useState<Record<string, string>>({});
  const [insights, setInsights] = useState<InsightReport | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedReadings = loadReadings();
    const storedCycles = loadCycles();
    const storedSnapshots = loadSnapshots();
    const storedBaselines = loadBaselines();
    queueMicrotask(() => {
      setReadings(storedReadings);
      setCycles(storedCycles);
      setSnapshots(storedSnapshots);
      setBaselines(storedBaselines);
      setTargetDrafts(Object.fromEntries(storedBaselines.map((item) => [item.cycle_id, item.target_kwh])));
      setReady(true);
    });
  }, []);

  useEffect(() => {
    if (!ready) {
      return;
    }
    saveCycles(cycles);
    saveBaselines(baselines);
  }, [ready, cycles, baselines]);

  useEffect(() => {
    if (!ready || !apiBase) {
      return;
    }
    const controller = new AbortController();
    fetch(`${apiBase}/api/history/insights`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({ cycles: cycles.map(toCycleInput) }),
    })
      .then(async (response) => {
        if (!response.ok) {
          setInsights(null);
          return;
        }
        setInsights((await response.json()) as InsightReport);
      })
      .catch((cause: unknown) => {
        if (!(cause instanceof DOMException && cause.name === "AbortError")) {
          setInsights(null);
        }
      });
    return () => controller.abort();
  }, [apiBase, ready, cycles]);

  async function saveCycle() {
    if (!apiBase || !startId || !endId) {
      setError("Choose a starting checkpoint and a later ending checkpoint.");
      return;
    }
    setError(null);
    const cycleId = editingId ?? crypto.randomUUID();
    const response = await fetch(`${apiBase}/api/history/cycles/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cycle_id: cycleId,
        start_checkpoint_id: startId,
        end_checkpoint_id: endId,
        readings: readings.map(toCheckpoint),
        existing_cycles: cycles.map(toExisting),
        ignore_cycle_id: editingId,
      }),
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const body = (await response.json()) as CycleValidation;
    if (body.status !== "accepted" || !body.cycle) {
      setError(body.detail);
      return;
    }
    setCycles((current) => {
      const without = current.filter((item) => item.id !== body.cycle?.id);
      return [...without, body.cycle as StoredCycle];
    });
    setMessage(body.detail);
    setEditingId(null);
    setStartId("");
    setEndId("");
  }

  async function compareSelected() {
    if (!apiBase) {
      return;
    }
    const earlier = cycles.find((item) => item.id === earlierId);
    const later = cycles.find((item) => item.id === laterId);
    if (!earlier || !later) {
      setError("Choose two saved cycles.");
      return;
    }
    const response = await fetch(`${apiBase}/api/history/cycles/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ earlier: toCycleInput(earlier), later: toCycleInput(later) }),
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    setComparison((await response.json()) as CycleComparison);
    setError(null);
  }

  async function compareSnapshot(snapshot: StoredSnapshot) {
    if (!apiBase) {
      return;
    }
    const cycle = cycles.find(
      (item) =>
        item.meter_reference === snapshot.meter_reference &&
        item.started_at.slice(0, 10) === snapshot.cycle_started_on &&
        item.ended_at.slice(0, 10) === snapshot.cycle_ends_on,
    );
    if (!cycle) {
      setError("No saved cycle matches this forecast's meter and dates.");
      setForecastResult(null);
      return;
    }
    const response = await fetch(`${apiBase}/api/history/forecast-comparisons`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot, cycle: toCycleInput(cycle) }),
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const body = (await response.json()) as ForecastComparison;
    setForecastResult(body);
    if (body.status === "calculated" && body.actual_kwh && body.forecast_kwh) {
      setForecastMatches((current) => [
        ...current.filter((item) => item.cycleId !== cycle.id),
        { cycleId: cycle.id, forecast: body.forecast_kwh as string, actual: body.actual_kwh as string },
      ]);
    }
    setError(null);
  }

  async function saveTarget(cycle: StoredCycle) {
    if (!apiBase) {
      return;
    }
    const target = (targetDrafts[cycle.id] ?? "").trim();
    const response = await fetch(`${apiBase}/api/history/baseline-comparisons`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cycle: toCycleInput(cycle), cycle_id: cycle.id, target_kwh: target }),
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const body = (await response.json()) as BaselineComparison;
    if (body.status !== "calculated" || !body.target_kwh) {
      setError(body.detail);
      return;
    }
    setBaselines((current) => [...current.filter((item) => item.cycle_id !== cycle.id), { cycle_id: cycle.id, target_kwh: body.target_kwh as string }]);
    setBaselineResults((current) => ({ ...current, [cycle.id]: body }));
    setError(null);
  }

  function removeCycle(id: string) {
    setCycles((current) => current.filter((item) => item.id !== id));
    setBaselines((current) => current.filter((item) => item.cycle_id !== id));
    setForecastMatches((current) => current.filter((item) => item.cycleId !== id));
    setPendingDelete(null);
    setMessage("The cycle was removed from this browser. The meter checkpoints were kept.");
  }

  const options = readings.map((item) => ({
    value: item.id,
    label: `${item.register_kwh} kWh · ${item.read_at.slice(0, 10)} · ${item.meter_reference ?? "No meter"}`,
  }));
  const cycleOptions = cycles.map((item) => ({
    value: item.id,
    label: `${item.started_at.slice(0, 10)} to ${item.ended_at.slice(0, 10)} · ${item.actual_kwh} kWh`,
  }));
  const pkr = insights?.pkr_impact ?? comparison?.pkr_impact ?? forecastResult?.pkr_impact;

  return (
    <div className="flex flex-col gap-5">
      <EmptyState
        icon={History}
        title="Measured use from confirmed checkpoints"
        description="A cycle needs two confirmed readings from the same meter. A forecast stays an estimate. A lower figure is measured use, not a rupee saving and not proof that an appliance caused it."
      />
      {!apiBase ? <p role="alert">The API address is not configured.</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {message ? <p className="text-sm leading-6">{message}</p> : null}

      <Card as="section" aria-labelledby="overview-heading">
        <h2 id="overview-heading" className="font-display text-lg font-semibold">
          What has been measured
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">Kept only in this browser. This is not a cloud backup, and another device cannot see it.</p>
        {insights && insights.cycle_count > 0 ? (
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <Metric label="Recorded cycles" value={String(insights.cycle_count)} />
            <Metric label="Latest measured cycle" value={insights.latest_cycle_kwh ? `${insights.latest_cycle_kwh} kWh` : "Unavailable"} />
            <Metric label="Latest average per day" value={insights.latest_average_daily_kwh ? `${insights.latest_average_daily_kwh} kWh` : "Unavailable"} />
          </div>
        ) : (
          <p className="mt-4 text-sm leading-6">No measured cycles yet. Add one from two confirmed meter checkpoints. No sample history is included.</p>
        )}
        {insights && insights.insights.length > 0 ? (
          <ul className="mt-4 flex flex-col gap-3">
            {insights.insights.map((item) => (
              <li key={item.code}>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">{item.title}</h3>
                  <DataTrustChip status={chip(item.trust_status)} />
                </div>
                <p className="mt-1 text-sm leading-6">{item.detail}</p>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>

      <Card as="section" aria-labelledby="cycles-heading">
        <h2 id="cycles-heading" className="font-display text-lg font-semibold">
          Billing cycles
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          The registers shown here are the ones accepted when the cycle was saved. Deleting a cycle does not delete the meter checkpoints.
        </p>
        {readings.length < 2 ? (
          <p className="mt-4 text-sm leading-6">Confirm at least two meter checkpoints before a cycle can be saved.</p>
        ) : (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Select label="Starting checkpoint" value={startId} onChange={(event) => setStartId(event.target.value)} options={[{ value: "", label: "Choose a checkpoint" }, ...options]} />
            <Select label="Ending checkpoint" value={endId} onChange={(event) => setEndId(event.target.value)} options={[{ value: "", label: "Choose a later checkpoint" }, ...options]} />
          </div>
        )}
        <div className="mt-4">
          <Button type="button" onClick={() => void saveCycle()}>{editingId ? "Save cycle" : "Create cycle"}</Button>
        </div>
        {cycles.length === 0 ? null : (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-0 text-left text-sm">
              <caption className="sr-only">Saved billing cycles</caption>
              <thead>
                <tr>
                  <th scope="col" className="py-2 font-medium">Dates</th>
                  <th scope="col" className="py-2 font-medium">Days</th>
                  <th scope="col" className="py-2 font-medium">Measured kWh</th>
                  <th scope="col" className="py-2 font-medium">Meter</th>
                </tr>
              </thead>
              <tbody>
                {cycles.map((cycle) => {
                  const missing = !readings.some((item) => item.id === cycle.start_checkpoint_id) || !readings.some((item) => item.id === cycle.end_checkpoint_id);
                  const baseline = baselineResults[cycle.id];
                  return (
                    <tr key={cycle.id} className="border-t border-line align-top">
                      <td className="py-3 pr-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span>{cycle.started_at.slice(0, 10)} to {cycle.ended_at.slice(0, 10)}</span>
                          <DataTrustChip status="calculated" />
                        </div>
                        {missing ? <p className="mt-1 text-sm leading-6">A source checkpoint is no longer in the meter list. The registers below are the ones saved with this cycle.</p> : null}
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Button type="button" variant="secondary" onClick={() => { setEditingId(cycle.id); setStartId(cycle.start_checkpoint_id); setEndId(cycle.end_checkpoint_id); }}>Change checkpoints</Button>
                          {pendingDelete === cycle.id ? (
                            <>
                              <Button type="button" onClick={() => removeCycle(cycle.id)}>Confirm delete</Button>
                              <Button type="button" variant="ghost" onClick={() => setPendingDelete(null)}>Keep it</Button>
                            </>
                          ) : (
                            <Button type="button" variant="ghost" onClick={() => setPendingDelete(cycle.id)}>Delete cycle</Button>
                          )}
                        </div>
                        <div className="mt-3 max-w-xs">
                          <Input
                            label="Your kWh target for this cycle"
                            inputMode="decimal"
                            value={targetDrafts[cycle.id] ?? ""}
                            onChange={(event) => setTargetDrafts({ ...targetDrafts, [cycle.id]: event.target.value })}
                            hint="A figure you enter. Not a verified baseline."
                          />
                          <div className="mt-2">
                            <Button type="button" variant="secondary" onClick={() => void saveTarget(cycle)}>Compare with target</Button>
                          </div>
                          {baseline ? <p className="mt-2 text-sm leading-6">{baseline.detail}</p> : null}
                        </div>
                      </td>
                      <td className="py-3 font-mono">{cycle.duration_days}</td>
                      <td className="py-3 font-mono">{cycle.actual_kwh}</td>
                      <td className="py-3">{cycle.meter_reference}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card as="section" aria-labelledby="chart-heading">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="chart-heading" className="font-display text-lg font-semibold">
            Measured use by cycle
          </h2>
          <DataTrustChip status={cycles.length > 0 ? "calculated" : "unavailable"} />
        </div>
        {cycles.length > 0 ? (
          <div className="mt-4">
            <HistoryChart cycles={cycles} forecasts={forecastMatches} />
          </div>
        ) : (
          <p className="mt-3 text-sm leading-6">The chart stays empty until a cycle is saved. Missing cycles are not filled in.</p>
        )}
      </Card>

      <Card as="section" aria-labelledby="compare-heading">
        <h2 id="compare-heading" className="font-display text-lg font-semibold">
          Compare two cycles
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Select label="Earlier cycle" value={earlierId} onChange={(event) => setEarlierId(event.target.value)} options={[{ value: "", label: "Choose a cycle" }, ...cycleOptions]} />
          <Select label="Later cycle" value={laterId} onChange={(event) => setLaterId(event.target.value)} options={[{ value: "", label: "Choose a later cycle" }, ...cycleOptions]} />
        </div>
        <div className="mt-4">
          <Button type="button" onClick={() => void compareSelected()}>Compare cycles</Button>
        </div>
        {comparison ? (
          <div className="mt-4">
            <DataTrustChip status={comparison.status === "calculated" ? "calculated" : "unavailable"} />
            <p className="mt-2 text-sm leading-6">{comparison.detail}</p>
            {comparison.duration_warning ? <p className="mt-2 text-sm leading-6">{comparison.duration_warning}</p> : null}
            {comparison.earlier && comparison.later ? (
              <p className="mt-2 font-mono text-sm">
                Earlier {comparison.earlier.actual_kwh} kWh over {comparison.earlier.duration_days} days.
                Later {comparison.later.actual_kwh} kWh over {comparison.later.duration_days} days.
              </p>
            ) : null}
          </div>
        ) : (
          <p className="mt-4 text-sm leading-6">Choose two cycles from the same meter. Different lengths are shown with a warning.</p>
        )}
      </Card>

      <Card as="section" aria-labelledby="forecast-heading">
        <h2 id="forecast-heading" className="font-display text-lg font-semibold">
          Forecast and what was measured
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          A saved forecast is a previous estimate. Comparing it with a finished cycle does not score the model.
        </p>
        {snapshots.length === 0 ? (
          <p className="mt-4 text-sm leading-6">Save a forecast from the Forecast page when an estimate is available. An unavailable forecast is not saved.</p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {snapshots.map((snapshot) => (
              <li key={snapshot.id} className="rounded-xl border border-line p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">{snapshot.cycle_started_on} to {snapshot.cycle_ends_on}</h3>
                  <DataTrustChip status="estimated" />
                </div>
                <p className="mt-2 font-mono text-sm">Saved forecast {snapshot.projected_cycle_kwh} kWh</p>
                <p className="mt-1 text-sm leading-6">{snapshot.detail}</p>
                <div className="mt-3">
                  <Button type="button" variant="secondary" onClick={() => void compareSnapshot(snapshot)}>Compare with the measured cycle</Button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {forecastResult ? (
          <div className="mt-4">
            <div className="flex flex-wrap items-center gap-2">
              <DataTrustChip status={chip(forecastResult.actual_trust_status)} />
              <DataTrustChip status={chip(forecastResult.forecast_trust_status)} />
            </div>
            <p className="mt-2 text-sm leading-6">{forecastResult.detail}</p>
            {forecastResult.actual_kwh ? (
              <p className="mt-2 font-mono text-sm">
                Measured {forecastResult.actual_kwh} kWh. Forecast {forecastResult.forecast_kwh} kWh.
              </p>
            ) : null}
          </div>
        ) : null}
      </Card>

      <Card as="section" aria-labelledby="pkr-heading">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="pkr-heading" className="font-display text-lg font-semibold">
            Rupee savings
          </h2>
          <DataTrustChip status="unavailable" />
        </div>
        <p className="mt-3 text-sm leading-6">
          {pkr?.reason ?? "PKR savings are unavailable until a complete payable tariff can price both periods. No electricity rate is assumed."}
        </p>
        {pkr && pkr.missing_components.length > 0 ? (
          <p className="mt-2 text-sm leading-6 text-muted">Missing from the loaded tariffs: {pkr.missing_components.join(", ")}.</p>
        ) : null}
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <h3 className="text-sm font-semibold">{label}</h3>
      <p className="mt-1 font-mono text-sm">{value}</p>
    </div>
  );
}

function toCheckpoint(reading: StoredReading) {
  return {
    id: reading.id,
    register_kwh: reading.register_kwh,
    read_at: reading.read_at,
    meter_reference: reading.meter_reference,
    confirmed: true,
  };
}

function toExisting(cycle: StoredCycle) {
  return {
    id: cycle.id,
    meter_reference: cycle.meter_reference,
    start_checkpoint_id: cycle.start_checkpoint_id,
    end_checkpoint_id: cycle.end_checkpoint_id,
    started_at: cycle.started_at,
    ended_at: cycle.ended_at,
  };
}

function toCycleInput(cycle: StoredCycle) {
  return {
    ...toExisting(cycle),
    start_register_kwh: cycle.start_register_kwh,
    end_register_kwh: cycle.end_register_kwh,
  };
}

function chip(status: string): DataTrustStatus {
  const key = status.toLowerCase();
  if (key === "verified" || key === "calculated" || key === "extracted" || key === "estimated" || key === "unavailable") {
    return key;
  }
  return "unavailable";
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { message?: string; detail?: { msg?: string }[] | string };
    if (typeof body.message === "string" && body.message.trim()) {
      return body.message;
    }
    if (Array.isArray(body.detail) && typeof body.detail[0]?.msg === "string") {
      return body.detail[0].msg;
    }
  } catch {
    return "The request could not be completed.";
  }
  return "Check the cycle and try again.";
}
