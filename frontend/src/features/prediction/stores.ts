/** Budget and cycle dates stay in this browser, apart from meter checkpoints. */

const BUDGET_KEY = "bijlibachat.budget.v1";
const CYCLE_KEY = "bijlibachat.prediction-cycle.v1";

export type StoredBudget = {
  monthly_budget_pkr: string | null;
  monthly_kwh_target: string | null;
};

export type StoredCycle = {
  cycle_started_on: string;
  cycle_ends_on: string;
  cycle_start_register_kwh: string;
  meter_reference: string;
  provider_code: string;
  tariff_type: string;
  eligibility: string;
};

const emptyCycle: StoredCycle = {
  cycle_started_on: "",
  cycle_ends_on: "",
  cycle_start_register_kwh: "",
  meter_reference: "",
  provider_code: "",
  tariff_type: "",
  eligibility: "",
};

export function loadBudget(): StoredBudget | null {
  return readJson(BUDGET_KEY, isBudget);
}

export function saveBudget(budget: StoredBudget): void {
  window.localStorage.setItem(BUDGET_KEY, JSON.stringify(budget));
}

export function clearBudget(): void {
  window.localStorage.removeItem(BUDGET_KEY);
}

export function loadCycle(): StoredCycle {
  return readJson(CYCLE_KEY, isCycle) ?? emptyCycle;
}

export function saveCycle(cycle: StoredCycle): void {
  window.localStorage.setItem(CYCLE_KEY, JSON.stringify(cycle));
}

function readJson<T>(key: string, guard: (value: unknown) => value is T): T | null {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return null;
    }
    const parsed: unknown = JSON.parse(raw);
    if (!guard(parsed)) {
      window.localStorage.removeItem(key);
      return null;
    }
    return parsed;
  } catch {
    window.localStorage.removeItem(key);
    return null;
  }
}

function isBudget(value: unknown): value is StoredBudget {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  const budget = record.monthly_budget_pkr;
  const target = record.monthly_kwh_target;
  return (
    (budget === null || typeof budget === "string") &&
    (target === null || typeof target === "string") &&
    (budget !== null || target !== null)
  );
}

function isCycle(value: unknown): value is StoredCycle {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return Object.keys(emptyCycle).every((key) => typeof record[key] === "string");
}
