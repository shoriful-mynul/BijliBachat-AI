/** Appliance records and scenario drafts stay in this browser. */

const APPLIANCE_KEY = "bijlibachat.appliances.v1";
const SCENARIO_KEY = "bijlibachat.appliance-scenario.v1";

export type StoredAppliance = {
  id: string;
  name: string;
  category: string | null;
  rated_watts: string;
  quantity: number;
  operating_hours_per_day: string;
  operating_days_per_week: number | null;
  notes: string | null;
};

export type ScenarioDraft = {
  days: string;
  changes: Record<string, { operating_hours_per_day: string; quantity: number; operating_days_per_week: number | null }>;
};

const emptyDraft: ScenarioDraft = { days: "", changes: {} };

export function loadAppliances(): StoredAppliance[] {
  const parsed = readJson(APPLIANCE_KEY);
  if (!Array.isArray(parsed)) {
    if (parsed !== null) {
      window.localStorage.removeItem(APPLIANCE_KEY);
    }
    return [];
  }
  const valid = parsed.filter(isAppliance);
  if (valid.length !== parsed.length) {
    window.localStorage.setItem(APPLIANCE_KEY, JSON.stringify(valid));
  }
  return valid;
}

export function saveAppliances(appliances: StoredAppliance[]): void {
  window.localStorage.setItem(APPLIANCE_KEY, JSON.stringify(appliances));
}

export function loadScenario(): ScenarioDraft {
  const parsed = readJson(SCENARIO_KEY);
  if (!isDraft(parsed)) {
    if (parsed !== null) {
      window.localStorage.removeItem(SCENARIO_KEY);
    }
    return emptyDraft;
  }
  return parsed;
}

export function saveScenario(draft: ScenarioDraft): void {
  window.localStorage.setItem(SCENARIO_KEY, JSON.stringify(draft));
}

function readJson(key: string): unknown {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as unknown;
  } catch {
    window.localStorage.removeItem(key);
    return null;
  }
}

function isAppliance(value: unknown): value is StoredAppliance {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "string" &&
    typeof record.name === "string" &&
    (record.category === null || typeof record.category === "string") &&
    typeof record.rated_watts === "string" &&
    typeof record.quantity === "number" &&
    typeof record.operating_hours_per_day === "string" &&
    (record.operating_days_per_week === null || typeof record.operating_days_per_week === "number") &&
    (record.notes === null || typeof record.notes === "string")
  );
}

function isDraft(value: unknown): value is ScenarioDraft {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return typeof record.days === "string" && !!record.changes && typeof record.changes === "object";
}
