export type PkrImpact = {
  value: string | null;
  trust_status: string;
  reason: string;
  missing_components: string[];
  comparable: boolean;
};

export type CycleValidation = {
  status: "accepted" | "rejected" | "unavailable";
  cycle: {
    id: string;
    meter_reference: string;
    start_checkpoint_id: string;
    end_checkpoint_id: string;
    started_at: string;
    ended_at: string;
    start_register_kwh: string;
    end_register_kwh: string;
    actual_kwh: string;
    duration_days: string;
    average_daily_kwh: string;
    trust_status: string;
    detail: string;
  } | null;
  detail: string;
  pkr_impact: PkrImpact;
};

export type CycleComparison = {
  status: "calculated" | "unavailable";
  durations_comparable: boolean;
  duration_warning: string | null;
  usage_difference_kwh: string | null;
  absolute_difference_kwh: string | null;
  percentage_difference: string | null;
  average_daily_difference_kwh: string | null;
  direction: "reduced" | "increased" | "unchanged" | "unavailable";
  detail: string;
  earlier: { actual_kwh: string; average_daily_kwh: string; duration_days: string } | null;
  later: { actual_kwh: string; average_daily_kwh: string; duration_days: string } | null;
  pkr_impact: PkrImpact;
};

export type ForecastSnapshotResult = {
  status: "estimated" | "unavailable";
  snapshot: {
    id: string;
    meter_reference: string | null;
    created_at: string;
    cycle_started_on: string;
    cycle_ends_on: string;
    cycle_start_register_kwh: string;
    latest_register_kwh: string;
    latest_checkpoint_id: string;
    projected_cycle_kwh: string;
    reading_ids: string[];
    assumptions: string[];
    trust_status: "Estimated";
    method: "checkpoint-pace-v1";
    detail: string;
  } | null;
  detail: string;
};

export type ForecastComparison = {
  status: "calculated" | "unavailable";
  direction: "higher" | "lower" | "equal" | "unavailable";
  actual_kwh: string | null;
  forecast_kwh: string | null;
  difference_kwh: string | null;
  absolute_difference_kwh: string | null;
  percentage_difference: string | null;
  actual_trust_status: string;
  forecast_trust_status: string;
  difference_trust_status: string;
  detail: string;
  pkr_impact: PkrImpact;
};

export type BaselineComparison = {
  status: "calculated" | "unavailable";
  direction: "higher" | "lower" | "equal" | "unavailable";
  actual_kwh: string | null;
  target_kwh: string | null;
  difference_kwh: string | null;
  detail: string;
  trust_status: string;
  pkr_impact: PkrImpact;
};

export type InsightReport = {
  status: "calculated" | "unavailable";
  cycle_count: number;
  latest_cycle_kwh: string | null;
  latest_average_daily_kwh: string | null;
  direction: "reduced" | "increased" | "unchanged" | "unavailable";
  insights: { code: string; title: string; detail: string; trust_status: string }[];
  pkr_impact: PkrImpact;
};
