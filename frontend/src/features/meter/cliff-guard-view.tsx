"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { getApiBaseUrl } from "@/lib/health";
import type { DataTrustStatus } from "@/types/trust";
import { ThresholdGauge } from "./gauge";
import { loadReadings, type StoredReading } from "./ledger";
import { ReadingList } from "./meter-capture";
import type { CliffReport, Quantity } from "./types";

export function CliffGuardView() {
  const apiBase = getApiBaseUrl();
  const [readings, setReadings] = useState<StoredReading[]>([]);
  const [meter, setMeter] = useState("");
  const [report, setReport] = useState<CliffReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cycleStart, setCycleStart] = useState("");
  const [cycleEnd, setCycleEnd] = useState("");
  const [cycleRegister, setCycleRegister] = useState("");
  const [provider, setProvider] = useState("");
  const [tariffType, setTariffType] = useState("");
  const [eligibility, setEligibility] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const stored = loadReadings();
    const latest = stored.at(-1)?.meter_reference ?? "";
    queueMicrotask(() => {
      setReadings(stored);
      if (latest) {
        setMeter(latest);
      }
    });
  }, []);

  useEffect(() => {
    if (!apiBase) {
      return;
    }
    const selected = readings.filter((item) => (item.meter_reference ?? "") === meter);
    const controller = new AbortController();
    queueMicrotask(() => setLoading(true));
    fetch(`${apiBase}/api/cliff-guard`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        as_of: new Date().toISOString(),
        meter_reference: meter || null,
        readings: selected.map((item) => ({
          id: item.id,
          register_kwh: item.register_kwh,
          read_at: item.read_at,
          meter_reference: item.meter_reference,
          capture_method: item.capture_method,
          trust_status: item.trust_status,
        })),
        provider_code: provider.trim() || null,
        consumer_category: provider.trim() ? "residential" : null,
        tariff_type: tariffType || null,
        eligibility: eligibility || null,
        billing_date: provider.trim() && tariffType ? new Date().toISOString().slice(0, 10) : null,
        cycle_started_on: cycleStart || null,
        cycle_ends_on: cycleEnd || null,
        cycle_start_register_kwh: cycleRegister.trim() || null,
      }),
    })
      .then(async (response) => {
        if (!response.ok) {
          setError(await response.text());
          return;
        }
        setReport((await response.json()) as CliffReport);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (!(cause instanceof DOMException && cause.name === "AbortError")) {
          setError("Cliff Guard could not be calculated.");
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [apiBase, readings, meter, cycleStart, cycleEnd, cycleRegister, provider, tariffType, eligibility]);

  const verified = report?.threshold_status === "verified" && report.threshold_kwh && report.billing_cycle_consumption_kwh.value;

  return (
    <div className="flex flex-col gap-5">
      <EmptyState
        icon={Shield}
        title="Where this household stands between checkpoints"
        description="Cliff Guard uses readings you confirmed on this device. It does not watch the meter continuously. A threshold appears only when a dated tariff file contains a verified one."
        action={<Button href="/meter-readings">Record a checkpoint</Button>}
      />
      {!apiBase ? <p role="alert">The API address is not configured.</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {loading ? <p className="text-sm text-muted">Calculating from the checkpoints on this device.</p> : null}

      <Card as="section" aria-labelledby="status-heading">
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="status-heading" className="font-display text-lg font-semibold">
            Current meter status
          </h2>
          {report?.latest_reading ? <DataTrustChip status={chip(report.latest_reading.trust_status)} /> : <DataTrustChip status="unavailable" />}
        </div>
        {report?.latest_reading ? (
          <p className="mt-3 font-mono text-lg">{report.latest_reading.register_kwh} kWh</p>
        ) : (
          <p className="mt-3 text-sm leading-6">No checkpoint yet. Record one before consumption can be calculated.</p>
        )}
        <p className="mt-2 text-sm text-muted">
          Last updated {report?.last_updated ? formatWhen(report.last_updated) : "not available"}.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Fact label="Since the previous checkpoint" quantity={report?.consumption_kwh} period={report?.observation_period} />
          <Fact label="Average daily use" quantity={report?.average_daily_kwh} period={report?.observation_period} />
        </div>
      </Card>

      <Card as="section" aria-labelledby="threshold-heading">
        <h2 id="threshold-heading" className="font-display text-lg font-semibold">
          Threshold
        </h2>
        {verified && report?.threshold_kwh && report.billing_cycle_consumption_kwh.value ? (
          <div className="mt-4">
            <ThresholdGauge
              consumption={report.billing_cycle_consumption_kwh.value}
              threshold={report.threshold_kwh}
              remaining={report.remaining_kwh.value}
            />
            <Fact label="Safe daily allowance" quantity={report.safe_daily_allowance_kwh} />
          </div>
        ) : (
          <p className="mt-3 max-w-2xl text-sm leading-6">
            {report?.remaining_kwh.detail ?? "Threshold needs verification for this tariff configuration."}
            {report?.threshold_source ? ` The resolved file is ${report.threshold_source}.` : ""}
          </p>
        )}
        <p className="mt-3 text-sm leading-6">{report?.projection.message}</p>
        {report?.projection.projected_date ? (
          <p className="mt-2 text-sm">Projected date {report.projection.projected_date}. This estimate assumes the observed pace continues.</p>
        ) : null}
      </Card>

      <Card as="section" aria-labelledby="cycle-heading">
        <h2 id="cycle-heading" className="font-display text-lg font-semibold">
          Billing cycle, if you know it
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Leave these blank when the cycle start reading is not known. An older checkpoint is not treated as the start of the bill. The company and tariff fields are used only to look for a verified threshold. They do not classify the household.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <Input label="Cycle start date" type="date" value={cycleStart} onChange={(event) => setCycleStart(event.target.value)} />
          <Input label="Cycle end date" type="date" value={cycleEnd} onChange={(event) => setCycleEnd(event.target.value)} />
          <Input label="Register at cycle start" inputMode="decimal" value={cycleRegister} onChange={(event) => setCycleRegister(event.target.value)} />
          <Input label="Distribution company" value={provider} onChange={(event) => setProvider(event.target.value)} hint="Optional. For example IESCO." />
          <Select
            label="Tariff type"
            value={tariffType}
            onChange={(event) => setTariffType(event.target.value)}
            options={[
              { value: "", label: "Not selected" },
              { value: "non_tou", label: "Non time-of-use" },
              { value: "tou", label: "Time of use" },
            ]}
          />
          <Select
            label="Eligibility"
            value={eligibility}
            onChange={(event) => setEligibility(event.target.value)}
            options={[
              { value: "", label: "Not selected" },
              { value: "lifeline", label: "Lifeline" },
              { value: "protected", label: "Protected" },
              { value: "unprotected", label: "Unprotected" },
            ]}
          />
        </div>
        <div className="mt-4 max-w-sm">
          <Select
            label="Meter"
            value={meter}
            onChange={(event) => setMeter(event.target.value)}
            options={[
              { value: "", label: "Meter number not recorded" },
              ...Array.from(new Set(readings.map((item) => item.meter_reference).filter((item): item is string => Boolean(item)))).map((item) => ({
                value: item,
                label: item,
              })),
            ]}
          />
        </div>
        {report ? <Fact label="Billing-cycle consumption" quantity={report.billing_cycle_consumption_kwh} /> : null}
        {report && report.limitations.length > 0 ? (
          <ul className="mt-4 flex flex-col gap-1 text-sm text-muted">
            {report.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : null}
      </Card>
      <ReadingList
        readings={readings.filter((item) => (item.meter_reference ?? "") === meter)}
        intervals={report?.intervals ?? []}
      />
      <p className="text-sm">
        <Link href="/meter-readings" className="inline-flex min-h-12 items-center font-semibold underline">
          Add or review a checkpoint
        </Link>
      </p>
    </div>
  );
}

function Fact({ label, quantity, period }: { label: string; quantity?: Quantity; period?: string | null }) {
  if (!quantity) {
    return null;
  }
  return (
    <div className="mt-3">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold">{label}</h3>
        <DataTrustChip status={chip(quantity.trust_status)} />
      </div>
      <p className="mt-1 font-mono text-sm">{quantity.value ?? "Unavailable"}</p>
      <p className="mt-1 text-sm leading-6 text-muted">{quantity.detail}</p>
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

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
