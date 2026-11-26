"use client";

import { useMemo, useRef, useState } from "react";
import { FileSearch } from "lucide-react";
import { LocalizedNotice, SourceText } from "@/components/i18n/source-text";
import { useI18n } from "@/components/i18n/language-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { Select } from "@/components/ui/select";
import { getApiBaseUrl } from "@/lib/health";
import type { DataTrustStatus } from "@/types/trust";

type Confidence = "readable" | "uncertain" | "unreadable" | "missing";

type ExtractedField = {
  value: string | null;
  confidence: Confidence;
  readable: boolean;
  note: string | null;
  trust_status: string;
};

type ExtractionDraft = {
  confirmed: false;
  media_type: string;
  provider_code: ExtractedField;
  consumer_category: ExtractedField;
  tariff_type: ExtractedField;
  eligibility: ExtractedField;
  billing_date: ExtractedField;
  consumption_kwh: ExtractedField;
  peak_kwh: ExtractedField;
  off_peak_kwh: ExtractedField;
  sanctioned_load_kw: ExtractedField;
  energy_charge: ExtractedField;
  fixed_charge: ExtractedField;
  fuel_price_adjustment: ExtractedField;
  gst: ExtractedField;
  electricity_duty: ExtractedField;
  tv_fee: ExtractedField;
  arrears: ExtractedField;
  total_amount_due: ExtractedField;
  limitations: string[];
};

type Comparison = {
  code: string;
  label: string;
  reported_amount: string | null;
  calculated_amount: string | null;
  difference: string | null;
  outcome: "match" | "possible_mismatch" | "not_comparable" | "unavailable";
  trust_status: string;
  explanation: string;
};

type AuditReport = {
  provider_code: string;
  consumer_category: string;
  billing_period: string;
  confirmed: "user_confirmed";
  config_id: string | null;
  config_version: string | null;
  source: { document_title: string; source_url: string; reference: string } | null;
  comparisons: Comparison[];
  missing_inputs: string[];
  limitations: string[];
  complete_payable_comparison: boolean;
  overall_trust_status: string;
  explanation: string;
};

type FormState = {
  provider_code: string;
  consumer_category: string;
  tariff_type: string;
  eligibility: string;
  billing_date: string;
  consumption_kwh: string;
  peak_kwh: string;
  off_peak_kwh: string;
  sanctioned_load_kw: string;
  maximum_demand_kw: string;
  phase: string;
  energy_charge: string;
  fixed_charge: string;
  fuel_price_adjustment: string;
  gst: string;
  electricity_duty: string;
  tv_fee: string;
  arrears: string;
  total_amount_due: string;
};

const emptyForm: FormState = {
  provider_code: "",
  consumer_category: "",
  tariff_type: "",
  eligibility: "",
  billing_date: "",
  consumption_kwh: "",
  peak_kwh: "",
  off_peak_kwh: "",
  sanctioned_load_kw: "",
  maximum_demand_kw: "",
  phase: "",
  energy_charge: "",
  fixed_charge: "",
  fuel_price_adjustment: "",
  gst: "",
  electricity_duty: "",
  tv_fee: "",
  arrears: "",
  total_amount_due: "",
};

const moneyFields = [
  ["energy_charge", "bill.energy"],
  ["fixed_charge", "bill.fixed"],
  ["fuel_price_adjustment", "bill.fpa"],
  ["gst", "bill.gst"],
  ["electricity_duty", "bill.duty"],
  ["tv_fee", "bill.tv"],
  ["arrears", "bill.arrears"],
  ["total_amount_due", "bill.total"],
] as const;

const outcomeKeys = {
  match: "bill.match",
  possible_mismatch: "bill.mismatch",
  not_comparable: "bill.notComparable",
  unavailable: "trust.unavailable",
} as const;

function trustChip(status: string): DataTrustStatus {
  const key = status.toLowerCase();
  if (
    key === "verified" ||
    key === "calculated" ||
    key === "extracted" ||
    key === "estimated" ||
    key === "unavailable"
  ) {
    return key;
  }
  return "unavailable";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isField(value: unknown): value is ExtractedField {
  if (!isRecord(value)) {
    return false;
  }
  return (
    (typeof value.value === "string" || value.value === null) &&
    (value.confidence === "readable" ||
      value.confidence === "uncertain" ||
      value.confidence === "unreadable" ||
      value.confidence === "missing") &&
    typeof value.readable === "boolean" &&
    typeof value.trust_status === "string"
  );
}

function isDraft(value: unknown): value is ExtractionDraft {
  if (!isRecord(value) || value.confirmed !== false) {
    return false;
  }
  return (
    isField(value.provider_code) &&
    isField(value.energy_charge) &&
    isField(value.consumption_kwh) &&
    isField(value.total_amount_due)
  );
}

function isAudit(value: unknown): value is AuditReport {
  return (
    isRecord(value) &&
    value.confirmed === "user_confirmed" &&
    Array.isArray(value.comparisons) &&
    typeof value.explanation === "string" &&
    typeof value.complete_payable_comparison === "boolean"
  );
}

function formFromDraft(draft: ExtractionDraft): FormState {
  const next = { ...emptyForm };
  const record = draft as unknown as Record<string, unknown>;
  (Object.keys(emptyForm) as (keyof FormState)[]).forEach((key) => {
    const field = record[key];
    if (isField(field) && field.value) {
      next[key] = field.value;
    }
  });
  return next;
}

function blank(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function auditBody(form: FormState): Record<string, unknown> {
  return {
    confirmation: "user_confirmed",
    provider_code: form.provider_code.trim(),
    consumer_category: form.consumer_category.trim(),
    tariff_type: form.tariff_type,
    eligibility: blank(form.eligibility),
    billing_date: form.billing_date,
    consumption_kwh: form.consumption_kwh.trim(),
    peak_kwh: blank(form.peak_kwh),
    off_peak_kwh: blank(form.off_peak_kwh),
    sanctioned_load_kw: blank(form.sanctioned_load_kw),
    maximum_demand_kw: blank(form.maximum_demand_kw),
    phase: blank(form.phase),
    energy_charge: blank(form.energy_charge),
    fixed_charge: blank(form.fixed_charge),
    fuel_price_adjustment: blank(form.fuel_price_adjustment),
    gst: blank(form.gst),
    electricity_duty: blank(form.electricity_duty),
    tv_fee: blank(form.tv_fee),
    arrears: blank(form.arrears),
    total_amount_due: blank(form.total_amount_due),
    other_charges: [],
  };
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { message?: string; detail?: unknown };
    if (typeof body.message === "string" && body.message.trim()) {
      return body.message;
    }
  } catch {
    return "The request could not be completed.";
  }
  return "Check the values and try again.";
}

export function BillAuditor() {
  const { t } = useI18n();
  const apiBase = getApiBaseUrl();
  const abortRef = useRef<AbortController | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<"empty" | "uploading" | "review" | "auditing">("empty");
  const [draft, setDraft] = useState<ExtractionDraft | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [reviewed, setReviewed] = useState(false);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [complaint, setComplaint] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const extractedNotes = useMemo(() => {
    if (!draft) {
      return {};
    }
    const notes: Partial<Record<keyof FormState, ExtractedField>> = {};
    const record = draft as unknown as Record<string, unknown>;
    (Object.keys(emptyForm) as (keyof FormState)[]).forEach((key) => {
      const field = record[key];
      if (isField(field)) {
        notes[key] = field;
      }
    });
    return notes;
  }, [draft]);

  function reset() {
    abortRef.current?.abort();
    setFile(null);
    setStep("empty");
    setDraft(null);
    setForm(emptyForm);
    setReviewed(false);
    setReport(null);
    setComplaint(null);
    setError(null);
    setCopied(false);
  }

  function edit(key: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
    setReviewed(false);
    setReport(null);
    setComplaint(null);
  }

  async function upload() {
    if (!file || !apiBase || step === "uploading") {
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setStep("uploading");
    setError(null);
    setReport(null);
    setComplaint(null);
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${apiBase}/api/bills/extractions`, {
        method: "POST",
        body,
        signal: controller.signal,
      });
      if (!response.ok) {
        setError(await readError(response));
        setStep("empty");
        return;
      }
      const payload: unknown = await response.json();
      if (!isDraft(payload)) {
        setError("The bill could not be read. No values were extracted.");
        setStep("empty");
        return;
      }
      setDraft(payload);
      setForm(formFromDraft(payload));
      setReviewed(false);
      setStep("review");
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") {
        setStep("empty");
        return;
      }
      setError("The bill could not be read. No values were extracted.");
      setStep("empty");
    }
  }

  async function audit() {
    if (!apiBase || !reviewed || step === "auditing") {
      return;
    }
    setStep("auditing");
    setError(null);
    try {
      const response = await fetch(`${apiBase}/api/bills/audits`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(auditBody(form)),
      });
      if (!response.ok) {
        setError(await readError(response));
        setStep("review");
        return;
      }
      const payload: unknown = await response.json();
      if (!isAudit(payload)) {
        setError("The audit could not be shown.");
        setStep("review");
        return;
      }
      setReport(payload);
      setStep("review");
    } catch {
      setError("The audit could not be completed.");
      setStep("review");
    }
  }

  async function draftComplaint() {
    if (!apiBase || !reviewed) {
      return;
    }
    setError(null);
    const response = await fetch(`${apiBase}/api/bills/complaint-drafts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(auditBody(form)),
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const payload = (await response.json()) as { text?: string; submitted?: boolean };
    if (payload.submitted !== false || typeof payload.text !== "string") {
      setError("A complaint draft could not be prepared.");
      return;
    }
    setComplaint(payload.text);
    setCopied(false);
  }

  return (
    <div className="flex flex-col gap-5">
      <EmptyState
        icon={FileSearch}
        title={t("bill.introTitle")}
        description={t("bill.intro")}
      />

      <Card as="section" aria-labelledby="upload-heading">
        <h2 id="upload-heading" className="font-display text-lg font-semibold">
          {t("bill.uploadTitle")}
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{t("bill.uploadHelp")}</p>
        {!apiBase ? (
          <p className="mt-3 text-sm" role="alert">
            {t("common.apiMissing")}
          </p>
        ) : null}
        <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center">
          <input
            aria-label={t("bill.file")}
            type="file"
            accept="image/jpeg,image/png,image/webp,application/pdf,.jpg,.jpeg,.png,.webp,.pdf"
            className="block min-h-12 w-full text-sm file:me-3 file:min-h-12 file:rounded-xl file:border-0 file:bg-aqua file:px-4 file:font-semibold file:text-ink"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setError(null);
            }}
          />
          <Button
            type="button"
            className="shrink-0 whitespace-nowrap"
            onClick={upload}
            disabled={!file || !apiBase || step === "uploading"}
          >
            {t("bill.read")}
          </Button>
          <Button type="button" variant="ghost" className="shrink-0 whitespace-nowrap" onClick={reset}>
            {t("bill.reset")}
          </Button>
        </div>
        {step === "uploading" ? (
          <div className="mt-4 flex flex-col gap-3">
            <LoadingState label={t("bill.reading")} />
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                abortRef.current?.abort();
              }}
            >
              {t("bill.cancel")}
            </Button>
          </div>
        ) : null}
        {error ? (
          <p className="mt-3 text-sm" role="alert">
            <LocalizedNotice value={error} />
          </p>
        ) : null}
      </Card>

      {draft ? (
        <Card as="section" aria-labelledby="review-heading">
          <div className="flex flex-wrap items-center gap-3">
            <h2 id="review-heading" className="font-display text-lg font-semibold">
              {t("bill.reviewTitle")}
            </h2>
            <DataTrustChip status="extracted" />
          </div>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{t("bill.reviewHelp")}</p>
          <ul className="mt-3 flex flex-col gap-1 text-sm text-muted">
            {draft.limitations.map((item) => (
              <li key={item}><SourceText>{item}</SourceText></li>
            ))}
          </ul>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <Field
              label={t("bill.company")}
              value={form.provider_code}
              extracted={extractedNotes.provider_code}
              inputMode="text"
              onChange={(value) => edit("provider_code", value)}
            />
            <Select
              label={t("bill.category")}
              hint={noteFor(extractedNotes.consumer_category)}
              value={form.consumer_category}
              onChange={(event) => edit("consumer_category", event.target.value)}
              options={[
                { value: "", label: t("bill.notConfirmed") },
                { value: "residential", label: t("bill.residential") },
              ]}
            />
            <Select
              label={t("forecast.tariffType")}
              hint={noteFor(extractedNotes.tariff_type)}
              value={form.tariff_type}
              onChange={(event) => edit("tariff_type", event.target.value)}
              options={[
                { value: "", label: t("bill.notConfirmed") },
                { value: "non_tou", label: t("forecast.nonTou") },
                { value: "tou", label: t("forecast.tou") },
              ]}
            />
            <Select
              label={t("forecast.eligibilityShort")}
              hint={noteFor(extractedNotes.eligibility) ?? t("bill.eligibilityHint")}
              value={form.eligibility}
              onChange={(event) => edit("eligibility", event.target.value)}
              options={[
                { value: "", label: t("bill.notConfirmed") },
                { value: "lifeline", label: t("forecast.lifeline") },
                { value: "protected", label: t("forecast.protected") },
                { value: "unprotected", label: t("forecast.unprotected") },
              ]}
            />
            <Input
              label={t("bill.billingDate")}
              type="date"
              value={form.billing_date}
              hint={noteFor(extractedNotes.billing_date)}
              onChange={(event) => edit("billing_date", event.target.value)}
            />
            <Field
              label={t("bill.units")}
              value={form.consumption_kwh}
              extracted={extractedNotes.consumption_kwh}
              onChange={(value) => edit("consumption_kwh", value)}
            />
            <Field
              label={t("bill.peak")}
              value={form.peak_kwh}
              extracted={extractedNotes.peak_kwh}
              onChange={(value) => edit("peak_kwh", value)}
            />
            <Field
              label={t("bill.offPeak")}
              value={form.off_peak_kwh}
              extracted={extractedNotes.off_peak_kwh}
              onChange={(value) => edit("off_peak_kwh", value)}
            />
            <Field
              label={t("bill.load")}
              value={form.sanctioned_load_kw}
              extracted={extractedNotes.sanctioned_load_kw}
              onChange={(value) => edit("sanctioned_load_kw", value)}
            />
            <Select
              label={t("bill.phase")}
              value={form.phase}
              onChange={(event) => edit("phase", event.target.value)}
              options={[
                { value: "", label: t("bill.notConfirmed") },
                { value: "single", label: t("bill.single") },
                { value: "three", label: t("bill.three") },
              ]}
            />
            {moneyFields.map(([key, label]) => (
              <Field
                key={key}
                label={t(label)}
                value={form[key]}
                extracted={extractedNotes[key]}
                onChange={(value) => edit(key, value)}
              />
            ))}
          </div>
          <label className="mt-5 flex min-h-12 items-center gap-3 text-sm">
            <input
              type="checkbox"
              className="h-5 w-5"
              checked={reviewed}
              onChange={(event) => setReviewed(event.target.checked)}
            />
            {t("bill.confirmBox")}
          </label>
          <div className="mt-4 flex flex-col gap-3 sm:flex-row">
            <Button type="button" onClick={audit} disabled={!reviewed || step === "auditing"}>
              {step === "auditing" ? t("bill.comparing") : t("bill.auditAction")}
            </Button>
          </div>
        </Card>
      ) : null}

      {step === "auditing" ? <LoadingState label={t("bill.comparingState")} /> : null}

      {report ? (
        <Card as="section" aria-labelledby="audit-heading">
          <div className="flex flex-wrap items-center gap-3">
            <h2 id="audit-heading" className="font-display text-lg font-semibold">
              {t("bill.auditTitle")}
            </h2>
            <DataTrustChip status={trustChip(report.overall_trust_status)} />
            <span className="text-sm text-muted">{t("bill.confirmedByYou")}</span>
          </div>
          <p className="mt-2 max-w-2xl text-sm leading-6"><SourceText>{report.explanation}</SourceText></p>
          <p className="mt-2 text-sm text-muted">
            <bdi>{report.provider_code}</bdi> · <bdi>{report.consumer_category}</bdi> · <bdi>{report.billing_period}</bdi>
            {report.config_id ? <> · <bdi>{report.config_id} {report.config_version ?? ""}</bdi></> : ` · ${t("bill.noConfig")}`}
          </p>
          {report.source ? (
            <p className="mt-1 text-sm text-muted">
              {t("bill.source", { title: report.source.document_title, reference: report.source.reference })}
            </p>
          ) : null}
          {!report.complete_payable_comparison ? (
            <p className="mt-3 text-sm leading-6">{t("bill.incomplete")}</p>
          ) : null}
          {report.missing_inputs.length > 0 ? (
            <p className="mt-2 text-sm">{t("bill.missingInputs", { items: report.missing_inputs.join(", ") })}</p>
          ) : null}
          <div className="mt-4 flex flex-col gap-3">
            {report.comparisons.map((item) => (
              <article key={`${item.code}-${item.label}`} className="rounded-xl border border-line p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold"><bdi>{item.label}</bdi></h3>
                  <span className="text-sm">{t(outcomeKeys[item.outcome])}</span>
                  <DataTrustChip status={trustChip(item.trust_status)} />
                </div>
                <p className="mt-2 text-sm leading-6"><SourceText>{item.explanation}</SourceText></p>
                <p className="mt-1 font-mono text-sm">
                  {t("bill.amounts", {
                    reported: item.reported_amount ?? t("common.blank"),
                    calculated: item.calculated_amount ?? t("common.blank"),
                    difference: item.difference ? t("bill.difference", { amount: item.difference }) : "",
                  })}
                </p>
              </article>
            ))}
          </div>
          <ul className="mt-4 flex flex-col gap-1 text-sm text-muted">
            {report.limitations.map((item) => (
              <li key={item}><SourceText>{item}</SourceText></li>
            ))}
          </ul>
          <div className="mt-4">
            <Button type="button" variant="secondary" onClick={draftComplaint}>
              {t("bill.complaintAction")}
            </Button>
          </div>
        </Card>
      ) : null}

      {complaint !== null ? (
        <Card as="section" aria-labelledby="complaint-heading">
          <h2 id="complaint-heading" className="font-display text-lg font-semibold">
            {t("bill.complaintTitle")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted">{t("bill.complaintHelp")}</p>
          <label className="mt-4 block text-sm font-medium" htmlFor="complaint-draft">
            {t("bill.draftLabel")}
          </label>
          <textarea
            id="complaint-draft"
            className="mt-2 min-h-64 w-full rounded-xl border border-line bg-background p-3 text-sm leading-6"
            value={complaint}
            onChange={(event) => setComplaint(event.target.value)}
          />
          <div className="mt-3">
            <Button
              type="button"
              onClick={async () => {
                await navigator.clipboard.writeText(complaint);
                setCopied(true);
              }}
            >
              {copied ? t("bill.copied") : t("bill.copy")}
            </Button>
          </div>
        </Card>
      ) : null}
    </div>
  );
}

function noteFor(field: ExtractedField | undefined): string | undefined {
  if (!field) {
    return undefined;
  }
  const confidence = field.confidence === "missing" ? "Missing" : field.confidence;
  return [confidence, field.note].filter(Boolean).join(". ");
}

function Field({
  label,
  value,
  extracted,
  onChange,
  inputMode = "decimal",
}: {
  label: string;
  value: string;
  extracted?: ExtractedField;
  onChange: (value: string) => void;
  inputMode?: "decimal" | "text";
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <DataTrustChip status={extracted?.value ? "extracted" : "unavailable"} />
      </div>
      <Input
        label={label}
        inputMode={inputMode}
        value={value}
        hint={noteFor(extracted)}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}
