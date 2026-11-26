export type MeterDraft = {
  confirmed: false;
  reading_kwh: { value: string | null; confidence: string; note: string | null; trust_status: string };
  unit_label: { value: string | null; confidence: string; note: string | null };
  meter_reference: { value: string | null; confidence: string; note: string | null };
  requires_manual_review: boolean;
  limitations: string[];
};

export type ValidationResult = {
  accepted: boolean;
  outcome: "accepted" | "rejected" | "needs_review";
  explanation: string;
  warnings: string[];
  checkpoint: {
    id: string;
    household_id: string;
    register_kwh: string;
    read_at: string;
    capture_method: "manual" | "photo";
    trust_status: string;
    meter_reference: string | null;
    warnings: string[];
  } | null;
  storage: "not_retained";
};

export type Quantity = {
  value: string | null;
  trust_status: string;
  detail: string;
};

export type CliffReport = {
  latest_reading: { id: string; register_kwh: string; read_at: string; trust_status: string } | null;
  previous_reading: { register_kwh: string; read_at: string; trust_status: string } | null;
  consumption_kwh: Quantity;
  observation_period: string | null;
  average_daily_kwh: Quantity;
  billing_cycle_consumption_kwh: Quantity;
  billing_cycle_started_on: string | null;
  billing_cycle_ends_on: string | null;
  threshold_status: "verified" | "needs_verification" | "unavailable";
  threshold_kwh: string | null;
  threshold_source: string | null;
  remaining_kwh: Quantity;
  remaining_days: Quantity;
  safe_daily_allowance_kwh: Quantity;
  projection: {
    status: "estimated" | "unavailable";
    message: string;
    projected_date: string | null;
    trust_status: string;
    observation_period: string | null;
    assumptions: string[];
  };
  last_updated: string | null;
  missing_inputs: string[];
  limitations: string[];
  warnings: string[];
  intervals: { reading_id: string; consumed_kwh: string | null; trust_status: string; detail: string }[];
};
