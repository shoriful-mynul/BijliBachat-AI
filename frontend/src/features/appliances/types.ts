export type PkrImpact = {
  value: string | null;
  trust_status: string;
  reason: string;
  missing_components: string[];
  comparable: boolean;
};

export type ConsumptionReport = {
  status: "calculated" | "unavailable";
  total_daily_kwh: string | null;
  total_period_kwh: string | null;
  days: number | null;
  appliances: {
    id: string;
    name: string;
    daily_kwh: string;
    period_kwh: string | null;
    share_percent: string | null;
    trust_status: string;
    detail: string;
  }[];
  limitations: string[];
  pkr_impact: PkrImpact;
};

export type ScenarioReport = {
  status: "estimated" | "unavailable";
  direction: "reduced" | "increased" | "unchanged" | "unavailable";
  days: number;
  baseline_kwh: string | null;
  scenario_kwh: string | null;
  difference_kwh: string | null;
  percentage_difference: string | null;
  appliances: {
    id: string;
    name: string;
    direction: "reduced" | "increased" | "unchanged";
    baseline_kwh: string;
    scenario_kwh: string;
    difference_kwh: string;
    detail: string;
    trust_status: string;
  }[];
  pkr_impact: PkrImpact;
};

export type ActionPlanReport = {
  status: "estimated" | "unavailable";
  days: number;
  detail: string;
  actions: {
    title: string;
    appliance_id: string;
    appliance_name: string;
    baseline_assumption: string;
    proposed_assumption: string;
    difference_kwh: string;
    direction: "reduced" | "increased";
    trust_status: string;
    explanation: string;
  }[];
  pkr_impact: PkrImpact;
};
