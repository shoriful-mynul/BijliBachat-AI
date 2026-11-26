"use client";

import { useEffect, useState } from "react";
import { History } from "lucide-react";
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
  const { t } = useI18n();
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
    label: `${item.register_kwh} kWh · ${item.read_at.slice(0, 10)} · ${item.meter_reference ?? t("history.noMeter")}`,
  }));
  const cycleOptions = cycles.map((item) => ({
    value: item.id,
    label: `${item.started_at.slice(0, 10)} ${t("common.to")} ${item.ended_at.slice(0, 10)} · ${item.actual_kwh} kWh`,
  }));
  const pkr = insights?.pkr_impact ?? comparison?.pkr_impact ?? forecastResult?.pkr_impact;

  return (
    <div className="flex flex-col gap-5">
      <EmptyState
        icon={History}
        title={t("history.introTitle")}
        description={t("history.intro")}
      />
      {!apiBase ? <p role="alert">{t("common.apiMissing")}</p> : null}
      {error ? <p role="alert"><LocalizedNotice value={error} /></p> : null}
      {message ? <p className="text-sm leading-6"><LocalizedNotice value={message} /></p> : null}

      <Card as="section" aria-labelledby="overview-heading">
        <h2 id="overview-heading" className="font-display text-lg font-semibold">
          {t("history.measuredTitle")}
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">{t("history.local")}</p>
        {insights && insights.cycle_count > 0 ? (
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <Metric label={t("history.count")} value={String(insights.cycle_count)} />
            <Metric label={t("history.latest")} value={insights.latest_cycle_kwh ? `${insights.latest_cycle_kwh} kWh` : t("common.unavailable")} />
            <Metric label={t("history.latestDaily")} value={insights.latest_average_daily_kwh ? `${insights.latest_average_daily_kwh} kWh` : t("common.unavailable")} />
          </div>
        ) : (
          <p className="mt-4 text-sm leading-6">{t("history.empty")}</p>
        )}
        {insights && insights.insights.length > 0 ? (
          <ul className="mt-4 flex flex-col gap-3">
            {insights.insights.map((item) => (
              <li key={item.code}>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold"><SourceText>{item.title}</SourceText></h3>
                  <DataTrustChip status={chip(item.trust_status)} />
                </div>
                <p className="mt-1 text-sm leading-6"><SourceText>{item.detail}</SourceText></p>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>

      <Card as="section" aria-labelledby="cycles-heading">
        <h2 id="cycles-heading" className="font-display text-lg font-semibold">
          {t("history.cyclesTitle")}
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">{t("history.cyclesHelp")}</p>
        {readings.length < 2 ? (
          <p className="mt-4 text-sm leading-6">{t("history.needTwo")}</p>
        ) : (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Select label={t("history.startCheckpoint")} value={startId} onChange={(event) => setStartId(event.target.value)} options={[{ value: "", label: t("history.chooseCheckpoint") }, ...options]} />
            <Select label={t("history.endCheckpoint")} value={endId} onChange={(event) => setEndId(event.target.value)} options={[{ value: "", label: t("history.chooseLater") }, ...options]} />
          </div>
        )}
        <div className="mt-4">
          <Button type="button" onClick={() => void saveCycle()}>{editingId ? t("history.saveCycle") : t("history.createCycle")}</Button>
        </div>
        {cycles.length === 0 ? null : (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-0 text-start text-sm">
              <caption className="sr-only">{t("history.tableCaption")}</caption>
              <thead>
                <tr>
                  <th scope="col" className="py-2 font-medium">{t("history.dates")}</th>
                  <th scope="col" className="py-2 font-medium">{t("history.days")}</th>
                  <th scope="col" className="py-2 font-medium">{t("history.measuredKwh")}</th>
                  <th scope="col" className="py-2 font-medium">{t("history.meter")}</th>
                </tr>
              </thead>
              <tbody>
                {cycles.map((cycle) => {
                  const missing = !readings.some((item) => item.id === cycle.start_checkpoint_id) || !readings.some((item) => item.id === cycle.end_checkpoint_id);
                  const baseline = baselineResults[cycle.id];
                  return (
                    <tr key={cycle.id} className="border-t border-line align-top">
                      <td className="py-3 pe-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span>{cycle.started_at.slice(0, 10)} {t("common.to")} {cycle.ended_at.slice(0, 10)}</span>
                          <DataTrustChip status="calculated" />
                        </div>
                        {missing ? <p className="mt-1 text-sm leading-6">{t("history.missingCheckpoint")}</p> : null}
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Button type="button" variant="secondary" onClick={() => { setEditingId(cycle.id); setStartId(cycle.start_checkpoint_id); setEndId(cycle.end_checkpoint_id); }}>{t("history.change")}</Button>
                          {pendingDelete === cycle.id ? (
                            <>
                              <Button type="button" onClick={() => removeCycle(cycle.id)}>{t("history.confirmDelete")}</Button>
                              <Button type="button" variant="ghost" onClick={() => setPendingDelete(null)}>{t("history.keep")}</Button>
                            </>
                          ) : (
                            <Button type="button" variant="ghost" onClick={() => setPendingDelete(cycle.id)}>{t("history.delete")}</Button>
                          )}
                        </div>
                        <div className="mt-3 max-w-xs">
                          <Input
                            label={t("history.target")}
                            inputMode="decimal"
                            value={targetDrafts[cycle.id] ?? ""}
                            onChange={(event) => setTargetDrafts({ ...targetDrafts, [cycle.id]: event.target.value })}
                            hint={t("history.targetHint")}
                          />
                          <div className="mt-2">
                            <Button type="button" variant="secondary" onClick={() => void saveTarget(cycle)}>{t("history.compareTarget")}</Button>
                          </div>
                          {baseline ? <p className="mt-2 text-sm leading-6"><SourceText>{baseline.detail}</SourceText></p> : null}
                        </div>
                      </td>
                      <td className="py-3 font-mono">{cycle.duration_days}</td>
                      <td className="py-3 font-mono">{cycle.actual_kwh}</td>
                      <td className="py-3"><bdi>{cycle.meter_reference}</bdi></td>
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
            {t("history.chartTitle")}
          </h2>
          <DataTrustChip status={cycles.length > 0 ? "calculated" : "unavailable"} />
        </div>
        {cycles.length > 0 ? (
          <div className="mt-4">
            <HistoryChart cycles={cycles} forecasts={forecastMatches} />
          </div>
        ) : (
          <p className="mt-3 text-sm leading-6" role="status">{t("history.chartEmpty")}</p>
        )}
      </Card>

      <Card as="section" aria-labelledby="compare-heading">
        <h2 id="compare-heading" className="font-display text-lg font-semibold">
          {t("history.compareTitle")}
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Select label={t("history.earlier")} value={earlierId} onChange={(event) => setEarlierId(event.target.value)} options={[{ value: "", label: t("history.chooseCycle") }, ...cycleOptions]} />
          <Select label={t("history.later")} value={laterId} onChange={(event) => setLaterId(event.target.value)} options={[{ value: "", label: t("history.chooseLaterCycle") }, ...cycleOptions]} />
        </div>
        <div className="mt-4">
          <Button type="button" onClick={() => void compareSelected()}>{t("history.compare")}</Button>
        </div>
        {comparison ? (
          <div className="mt-4">
            <DataTrustChip status={comparison.status === "calculated" ? "calculated" : "unavailable"} />
            <p className="mt-2 text-sm leading-6"><SourceText>{comparison.detail}</SourceText></p>
            {comparison.duration_warning ? <p className="mt-2 text-sm leading-6"><SourceText>{comparison.duration_warning}</SourceText></p> : null}
            {comparison.earlier && comparison.later ? (
              <p className="mt-2 font-mono text-sm">
                {t("history.compareLine", {
                  earlier: comparison.earlier.actual_kwh,
                  earlierDays: comparison.earlier.duration_days,
                  later: comparison.later.actual_kwh,
                  laterDays: comparison.later.duration_days,
                })}
              </p>
            ) : null}
          </div>
        ) : (
          <p className="mt-4 text-sm leading-6">{t("history.compareEmpty")}</p>
        )}
      </Card>

      <Card as="section" aria-labelledby="forecast-heading">
        <h2 id="forecast-heading" className="font-display text-lg font-semibold">
          {t("history.forecastTitle")}
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">{t("history.forecastHelp")}</p>
        {snapshots.length === 0 ? (
          <p className="mt-4 text-sm leading-6">{t("history.noSnapshot")}</p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {snapshots.map((snapshot) => (
              <li key={snapshot.id} className="rounded-xl border border-line p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">{snapshot.cycle_started_on} {t("common.to")} {snapshot.cycle_ends_on}</h3>
                  <DataTrustChip status="estimated" />
                </div>
                <p className="mt-2 font-mono text-sm">{t("history.savedForecastLine", { kwh: snapshot.projected_cycle_kwh })}</p>
                <p className="mt-1 text-sm leading-6"><SourceText>{snapshot.detail}</SourceText></p>
                <div className="mt-3">
                  <Button type="button" variant="secondary" onClick={() => void compareSnapshot(snapshot)}>{t("history.compareSnapshot")}</Button>
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
            <p className="mt-2 text-sm leading-6"><SourceText>{forecastResult.detail}</SourceText></p>
            {forecastResult.actual_kwh ? (
              <p className="mt-2 font-mono text-sm">
                {t("history.measuredVsForecast", {
                  actual: forecastResult.actual_kwh,
                  forecast: forecastResult.forecast_kwh ?? "",
                })}
              </p>
            ) : null}
          </div>
        ) : null}
      </Card>

      <Card as="section" aria-labelledby="pkr-heading">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="pkr-heading" className="font-display text-lg font-semibold">
            {t("history.pkrTitle")}
          </h2>
          <DataTrustChip status="unavailable" />
        </div>
        <p className="mt-3 text-sm leading-6">
          {pkr?.reason ? <SourceText>{pkr.reason}</SourceText> : t("history.pkrFallback")}
        </p>
        {pkr && pkr.missing_components.length > 0 ? (
          <p className="mt-2 text-sm leading-6 text-muted">{t("common.missingTariffs", { items: pkr.missing_components.join(", ") })}</p>
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
