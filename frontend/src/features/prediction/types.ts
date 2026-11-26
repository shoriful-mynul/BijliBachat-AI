export type ForecastQuantity = {
  value: string | null;
  trust_status: string;
  detail: string;
};

export type ForecastReport = {
  forecast_status: "estimated" | "unavailable";
  cycle_consumption_kwh: ForecastQuantity;
  average_daily_kwh: ForecastQuantity;
  projected_additional_kwh: ForecastQuantity;
  projected_cycle_kwh: ForecastQuantity;
  observation_period: string | null;
  observation_days: string | null;
  remaining_days: string | null;
  billing_cycle_ends_on: string | null;
  assumptions: string[];
  missing_inputs: string[];
  limitations: string[];
  series: {
    on: string;
    kwh: string;
    kind: "observed" | "estimated";
    trust_status: string;
    label: string;
  }[];
  bill_cost: {
    value: string | null;
    trust_status: string;
    reason: string;
    missing_components: string[];
    comparable_with_budget: boolean;
  };
  budget_comparison: {
    value: string | null;
    trust_status: string;
    reason: string;
    comparable_with_budget: boolean;
  };
  target_comparison: {
    status: "estimated" | "unavailable";
    direction: "higher" | "lower" | "equal" | "unavailable";
    projected_cycle_kwh: string | null;
    target_kwh: string | null;
    difference_kwh: string | null;
    trust_status: string;
    detail: string;
  };
  monthly_budget_pkr: string | null;
  monthly_kwh_target: string | null;
};

export type BudgetValidation = {
  monthly_budget_pkr: string | null;
  monthly_kwh_target: string | null;
  storage: "browser_only";
  limitation: string;
};
