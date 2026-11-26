"use client";

import { useEffect, useRef, useState } from "react";
import { Gauge } from "lucide-react";
import { LocalizedNotice, SourceText } from "@/components/i18n/source-text";
import { useI18n } from "@/components/i18n/language-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { getApiBaseUrl } from "@/lib/health";
import type { DataTrustStatus } from "@/types/trust";
import { householdId, loadReadings, rememberReading, type StoredReading } from "./ledger";
import type { CliffReport, MeterDraft, ValidationResult } from "./types";

export function MeterCapture() {
  const { t } = useI18n();
  const apiBase = getApiBaseUrl();
  const abortRef = useRef<AbortController | null>(null);
  const [readings, setReadings] = useState<StoredReading[]>([]);
  const [register, setRegister] = useState("");
  const [readAt, setReadAt] = useState("");
  const [meterReference, setMeterReference] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [draft, setDraft] = useState<MeterDraft | null>(null);
  const [extractedValue, setExtractedValue] = useState<string | null>(null);
  const [busy, setBusy] = useState<"upload" | "save" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [review, setReview] = useState<ValidationResult | null>(null);
  const [intervals, setIntervals] = useState<CliffReport["intervals"]>([]);

  useEffect(() => {
    const stored = loadReadings();
    const stamp = localInputValue();
    queueMicrotask(() => {
      setReadings(stored);
      setReadAt(stamp);
    });
  }, []);

  useEffect(() => {
    if (!apiBase) {
      return;
    }
    const controller = new AbortController();
    fetch(`${apiBase}/api/cliff-guard`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        as_of: new Date().toISOString(),
        readings: readings.map(toPrior),
      }),
    })
      .then(async (response) => {
        if (!response.ok) {
          return;
        }
        const body = (await response.json()) as CliffReport;
        setIntervals(body.intervals ?? []);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [apiBase, readings]);

  async function upload() {
    if (!file || !apiBase || busy) {
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy("upload");
    setError(null);
    setReview(null);
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${apiBase}/api/meter-readings/extractions`, {
        method: "POST",
        body,
        signal: controller.signal,
      });
      if (!response.ok) {
        setError(await readError(response));
        return;
      }
      const payload = (await response.json()) as MeterDraft;
      if (payload.confirmed !== false) {
        setError("The meter photo could not be read. No reading was extracted.");
        return;
      }
      setDraft(payload);
      setExtractedValue(payload.reading_kwh.value);
      setRegister(payload.reading_kwh.value ?? "");
      if (payload.meter_reference.value) {
        setMeterReference(payload.meter_reference.value);
      }
    } catch (cause) {
      if (!(cause instanceof DOMException && cause.name === "AbortError")) {
        setError("The meter photo could not be read. No reading was extracted.");
      }
    } finally {
      setBusy(null);
    }
  }

  async function save(reviewDecision?: "keep_as_submitted") {
    if (!apiBase || busy) {
      return;
    }
    setBusy("save");
    setError(null);
    const origin = draft ? (register.trim() === (extractedValue ?? "") ? "photo_confirmed" : "photo_corrected") : "manual";
    const response = await fetch(`${apiBase}/api/meter-readings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        household_id: householdId(),
        reading: {
          confirmation: "user_confirmed",
          register_kwh: register.trim(),
          read_at: new Date(readAt).toISOString(),
          capture_method: draft ? "photo" : "manual",
          meter_reference: meterReference.trim() || null,
          origin,
          review_decision: reviewDecision ?? null,
        },
        prior_readings: readings.map(toPrior),
      }),
    });
    setBusy(null);
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const result = (await response.json()) as ValidationResult;
    setReview(result);
    if (result.accepted && result.checkpoint) {
      setReadings(
        rememberReading({
          id: result.checkpoint.id,
          household_id: result.checkpoint.household_id,
          register_kwh: result.checkpoint.register_kwh,
          read_at: result.checkpoint.read_at,
          meter_reference: result.checkpoint.meter_reference,
          capture_method: result.checkpoint.capture_method,
          trust_status: result.checkpoint.trust_status,
          warnings: result.checkpoint.warnings,
        }),
      );
      setDraft(null);
      setRegister("");
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <EmptyState
        icon={Gauge}
        title={t("meter.introTitle")}
        description={t("meter.intro")}
      />
      <Card as="section" aria-labelledby="manual-heading">
        <h2 id="manual-heading" className="font-display text-lg font-semibold">
          {t("meter.recordTitle")}
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Input label={t("meter.register")} required inputMode="decimal" value={register} onChange={(event) => { setRegister(event.target.value); setReview(null); }} hint={draft ? confidenceHint(draft) : t("meter.registerHint")} />
          <Input label={t("meter.time")} required type="datetime-local" value={readAt} onChange={(event) => setReadAt(event.target.value)} />
          <Input label={t("meter.number")} value={meterReference} onChange={(event) => setMeterReference(event.target.value)} hint={t("meter.numberHint")} />
        </div>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            aria-label={t("meter.photo")}
            type="file"
            accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
            className="block min-h-12 w-full text-sm file:me-3 file:min-h-12 file:rounded-xl file:border-0 file:bg-aqua file:px-4 file:font-semibold file:text-ink"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <Button type="button" variant="secondary" className="shrink-0 whitespace-nowrap" disabled={!file || !apiBase || busy !== null} onClick={upload}>
            {t("meter.readPhoto")}
          </Button>
        </div>
        {busy === "upload" ? (
          <div className="mt-4 flex flex-col gap-3">
            <LoadingState label={t("meter.readingPhoto")} />
            <Button type="button" variant="ghost" onClick={() => abortRef.current?.abort()}>
              {t("meter.cancel")}
            </Button>
          </div>
        ) : null}
        {draft ? (
          <p className="mt-3 text-sm leading-6" role="status">
            {t("meter.extracted")} {draft.requires_manual_review ? t("meter.needsReview") : t("meter.checkDigits")}
          </p>
        ) : null}
        {error ? <p className="mt-3 text-sm" role="alert"><LocalizedNotice value={error} /></p> : null}
        {review && !review.accepted ? (
          <div className="mt-4 rounded-xl border border-line p-3">
            <p className="text-sm leading-6"><SourceText>{review.explanation}</SourceText></p>
            {review.outcome === "needs_review" ? (
              <Button type="button" className="mt-3" onClick={() => save("keep_as_submitted")}>
                {t("meter.keep")}
              </Button>
            ) : null}
          </div>
        ) : null}
        <div className="mt-4">
          <Button type="button" disabled={!register.trim() || !readAt || !apiBase || busy !== null} onClick={() => save()}>
            {busy === "save" ? t("meter.checking") : t("meter.confirm")}
          </Button>
        </div>
      </Card>
      <ReadingList readings={readings} intervals={intervals} />
    </div>
  );
}

export function ReadingList({
  readings,
  intervals = [],
}: {
  readings: StoredReading[];
  intervals?: { reading_id: string; consumed_kwh: string | null; trust_status: string; detail: string }[];
}) {
  const { t } = useI18n();
  return (
    <Card as="section" aria-labelledby="history-heading">
      <h2 id="history-heading" className="font-display text-lg font-semibold">
        {t("meter.listTitle")}
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted">{t("meter.listHelp")}</p>
      {readings.length === 0 ? <p className="mt-4 text-sm">{t("meter.empty")}</p> : null}
      <div className="mt-4 flex flex-col gap-3">
        {readings.map((reading) => {
          return (
            <article key={reading.id} className="rounded-xl border border-line p-3">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold">{formatWhen(reading.read_at)}</h3>
                <DataTrustChip status={chip(reading.trust_status)} />
              </div>
              <p className="mt-2 font-mono text-sm">
                {reading.register_kwh} kWh
                {reading.meter_reference ? <> · <bdi>{reading.meter_reference}</bdi></> : ` · ${t("meter.numberMissing")}`}
              </p>
              {intervals
                .filter((item) => item.reading_id === reading.id)
                .map((item) => (
                  <p key={item.reading_id} className="mt-1 text-sm leading-6">
                    {item.consumed_kwh ? `${t("meter.sincePrevious", { kwh: item.consumed_kwh })} ` : ""}
                    <SourceText>{item.detail}</SourceText>
                  </p>
                ))}
              {reading.warnings.map((warning) => (
                <p key={warning} className="mt-2 text-sm leading-6"><SourceText>{warning}</SourceText></p>
              ))}
            </article>
          );
        })}
      </div>
    </Card>
  );
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

function confidenceHint(draft: MeterDraft): string {
  return [draft.reading_kwh.confidence, draft.reading_kwh.note].filter(Boolean).join(". ");
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

function localInputValue(): string {
  const date = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { message?: string };
    if (typeof body.message === "string" && body.message.trim()) {
      return body.message;
    }
  } catch {
    return "The request could not be completed.";
  }
  return "Check the reading and try again.";
}
