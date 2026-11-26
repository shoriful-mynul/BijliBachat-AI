/** Measured cycles, saved forecasts, and targets stay in this browser. */

const CYCLE_KEY = "bijlibachat.history-cycles.v1";
const SNAPSHOT_KEY = "bijlibachat.forecast-snapshots.v1";
const BASELINE_KEY = "bijlibachat.history-baselines.v1";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const DECIMAL = /^\d{1,9}(\.\d{1,3})?$/;
const METER = /^[A-Za-z0-9-]{4,32}$/;

export type StoredCycle = {
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
};

export type StoredSnapshot = {
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
};

export type StoredBaseline = {
  cycle_id: string;
  target_kwh: string;
};

export function loadCycles(): StoredCycle[] {
  return readList(CYCLE_KEY, isCycle);
}

export function saveCycles(cycles: StoredCycle[]): void {
  window.localStorage.setItem(CYCLE_KEY, JSON.stringify(cycles));
}

export function loadSnapshots(): StoredSnapshot[] {
  return readList(SNAPSHOT_KEY, isSnapshot);
}

export function rememberSnapshot(snapshot: StoredSnapshot): StoredSnapshot[] {
  const next = [...loadSnapshots().filter((item) => item.id !== snapshot.id), snapshot];
  window.localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(next));
  return next;
}

export function loadBaselines(): StoredBaseline[] {
  return readList(BASELINE_KEY, isBaseline);
}

export function saveBaselines(baselines: StoredBaseline[]): void {
  window.localStorage.setItem(BASELINE_KEY, JSON.stringify(baselines));
}

function readList<T extends { id?: string; cycle_id?: string }>(key: string, guard: (value: unknown) => value is T): T[] {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return [];
    }
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      window.localStorage.removeItem(key);
      return [];
    }
    const valid = parsed.filter(guard);
    const seen = new Set<string>();
    const unique = valid.filter((item) => {
      const id = item.id ?? item.cycle_id ?? "";
      if (!id || seen.has(id)) {
        return false;
      }
      seen.add(id);
      return true;
    });
    if (unique.length !== parsed.length) {
      window.localStorage.setItem(key, JSON.stringify(unique));
    }
    return unique;
  } catch {
    window.localStorage.removeItem(key);
    return [];
  }
}

function isCycle(value: unknown): value is StoredCycle {
  if (!isRecord(value)) {
    return false;
  }
  const started = Date.parse(String(value.started_at));
  const ended = Date.parse(String(value.ended_at));
  return (
    isUuid(value.id) &&
    typeof value.meter_reference === "string" &&
    METER.test(value.meter_reference) &&
    isUuid(value.start_checkpoint_id) &&
    isUuid(value.end_checkpoint_id) &&
    value.start_checkpoint_id !== value.end_checkpoint_id &&
    Number.isFinite(started) &&
    Number.isFinite(ended) &&
    ended > started &&
    DECIMAL.test(String(value.start_register_kwh)) &&
    DECIMAL.test(String(value.end_register_kwh)) &&
    atLeast(String(value.start_register_kwh), String(value.end_register_kwh)) &&
    DECIMAL.test(String(value.actual_kwh)) &&
    DECIMAL.test(String(value.duration_days)) &&
    DECIMAL.test(String(value.average_daily_kwh)) &&
    value.trust_status === "Calculated" &&
    typeof value.detail === "string"
  );
}

function isSnapshot(value: unknown): value is StoredSnapshot {
  if (!isRecord(value)) {
    return false;
  }
  return (
    isUuid(value.id) &&
    (value.meter_reference === null || (typeof value.meter_reference === "string" && METER.test(value.meter_reference))) &&
    Number.isFinite(Date.parse(String(value.created_at))) &&
    /^\d{4}-\d{2}-\d{2}$/.test(String(value.cycle_started_on)) &&
    /^\d{4}-\d{2}-\d{2}$/.test(String(value.cycle_ends_on)) &&
    String(value.cycle_ends_on) >= String(value.cycle_started_on) &&
    DECIMAL.test(String(value.cycle_start_register_kwh)) &&
    DECIMAL.test(String(value.latest_register_kwh)) &&
    isUuid(value.latest_checkpoint_id) &&
    DECIMAL.test(String(value.projected_cycle_kwh)) &&
    Array.isArray(value.reading_ids) &&
    value.reading_ids.length > 0 &&
    value.reading_ids.every(isUuid) &&
    Array.isArray(value.assumptions) &&
    value.trust_status === "Estimated" &&
    value.method === "checkpoint-pace-v1" &&
    typeof value.detail === "string"
  );
}

function isBaseline(value: unknown): value is StoredBaseline {
  if (!isRecord(value)) {
    return false;
  }
  return isUuid(value.cycle_id) && DECIMAL.test(String(value.target_kwh)) && Number(value.target_kwh) > 0;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object";
}

function isUuid(value: unknown): value is string {
  return typeof value === "string" && UUID.test(value);
}

function atLeast(left: string, right: string): boolean {
  const pad = (value: string) => {
    const [whole, fraction = ""] = value.split(".");
    return whole.padStart(12, "0") + fraction.padEnd(3, "0");
  };
  return pad(right) >= pad(left);
}
