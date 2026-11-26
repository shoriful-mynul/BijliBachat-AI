/** Device-local checkpoints. Photos are not stored. Another device cannot see this list. */

const LEDGER_KEY = "bijlibachat.meter-ledger.v1";
const HOUSEHOLD_KEY = "bijlibachat.meter-household.v1";

export type StoredReading = {
  id: string;
  household_id: string;
  register_kwh: string;
  read_at: string;
  meter_reference: string | null;
  capture_method: "manual" | "photo";
  trust_status: string;
  warnings: string[];
};

export function householdId(): string {
  const existing = window.localStorage.getItem(HOUSEHOLD_KEY);
  if (existing) {
    return existing;
  }
  const created = window.crypto.randomUUID();
  window.localStorage.setItem(HOUSEHOLD_KEY, created);
  return created;
}

export function loadReadings(): StoredReading[] {
  try {
    const raw = window.localStorage.getItem(LEDGER_KEY);
    if (!raw) {
      return [];
    }
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(isStored).sort((left, right) => left.read_at.localeCompare(right.read_at));
  } catch {
    return [];
  }
}

export function rememberReading(reading: StoredReading): StoredReading[] {
  const next = [...loadReadings().filter((item) => item.id !== reading.id), reading].sort((left, right) =>
    left.read_at.localeCompare(right.read_at),
  );
  window.localStorage.setItem(LEDGER_KEY, JSON.stringify(next));
  return next;
}

function isStored(value: unknown): value is StoredReading {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "string" &&
    typeof record.household_id === "string" &&
    typeof record.register_kwh === "string" &&
    typeof record.read_at === "string" &&
    (typeof record.meter_reference === "string" || record.meter_reference === null) &&
    (record.capture_method === "manual" || record.capture_method === "photo") &&
    typeof record.trust_status === "string" &&
    Array.isArray(record.warnings)
  );
}
