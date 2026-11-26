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
  globalThis.localStorage.setItem(CYCLE_KEY, JSON.stringify(cycles));
}

export function loadSnapshots(): StoredSnapshot[] {
  return readList(SNAPSHOT_KEY, isSnapshot);
}

export function rememberSnapshot(snapshot: StoredSnapshot): StoredSnapshot[] {
  const next = [...loadSnapshots().filter((item) => item.id !== snapshot.id), snapshot];
  globalThis.localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(next));
  return next;
}

export function loadBaselines(): StoredBaseline[] {
  return readList(BASELINE_KEY, isBaseline);
}

export function saveBaselines(baselines: StoredBaseline[]): void {
  globalThis.localStorage.setItem(BASELINE_KEY, JSON.stringify(baselines));
}

function readList<T extends { id?: string; cycle_id?: string }>(key: string, guard: (value: unknown) => value is T): T[] {
  try {
    const raw = globalThis.localStorage.getItem(key);
    if (!raw) {
      return [];
    }
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      globalThis.localStorage.removeItem(key);
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
      globalThis.localStorage.setItem(key, JSON.stringify(unique));
    }
    return unique;
  } catch {
    globalThis.localStorage.removeItem(key);
    return [];
  }
}

function isCycle(value: unknown): value is StoredCycle {
  if (!isRecord(value)) {
    return false;
  }
  const started = timestampMicros(String(value.started_at));
  const ended = timestampMicros(String(value.ended_at));
  const startRegister = toMilli(String(value.start_register_kwh));
  const endRegister = toMilli(String(value.end_register_kwh));
  const actual = toMilli(String(value.actual_kwh));
  const duration = toMilli(String(value.duration_days));
  const average = toMilli(String(value.average_daily_kwh));
  if (
    started === null ||
    ended === null ||
    ended <= started ||
    startRegister === null ||
    endRegister === null ||
    endRegister < startRegister ||
    actual === null ||
    duration === null ||
    average === null
  ) {
    return false;
  }
  const elapsed = ended - started;
  const measured = endRegister - startRegister;
  return (
    isUuid(value.id) &&
    typeof value.meter_reference === "string" &&
    METER.test(value.meter_reference) &&
    isUuid(value.start_checkpoint_id) &&
    isUuid(value.end_checkpoint_id) &&
    value.start_checkpoint_id !== value.end_checkpoint_id &&
    value.trust_status === "Calculated" &&
    typeof value.detail === "string" &&
    actual === measured &&
    duration === roundHalfUp(elapsed, BigInt(86400000)) &&
    average === roundHalfUp(measured * BigInt("86400000000"), elapsed)
  );
}

function isSnapshot(value: unknown): value is StoredSnapshot {
  if (!isRecord(value)) {
    return false;
  }
  const readingIds = value.reading_ids;
  const startRegister = toMilli(String(value.cycle_start_register_kwh));
  const latestRegister = toMilli(String(value.latest_register_kwh));
  const projected = toMilli(String(value.projected_cycle_kwh));
  return (
    isUuid(value.id) &&
    (value.meter_reference === null || (typeof value.meter_reference === "string" && METER.test(value.meter_reference))) &&
    timestampMicros(String(value.created_at)) !== null &&
    isCalendarDate(String(value.cycle_started_on)) &&
    isCalendarDate(String(value.cycle_ends_on)) &&
    String(value.cycle_ends_on) >= String(value.cycle_started_on) &&
    startRegister !== null &&
    latestRegister !== null &&
    latestRegister >= startRegister &&
    projected !== null &&
    isUuid(value.latest_checkpoint_id) &&
    Array.isArray(readingIds) &&
    readingIds.length > 0 &&
    readingIds.every(isUuid) &&
    new Set(readingIds).size === readingIds.length &&
    readingIds.includes(value.latest_checkpoint_id) &&
    Array.isArray(value.assumptions) &&
    value.assumptions.every((item) => typeof item === "string") &&
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

const TIMESTAMP = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$/;
const CALENDAR_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

function isCalendarDate(value: string): boolean {
  const match = CALENDAR_DATE.exec(value);
  if (!match) {
    return false;
  }
  return isRealDate(Number(match[1]), Number(match[2]), Number(match[3]));
}

function timestampMicros(value: string): bigint | null {
  const match = TIMESTAMP.exec(value);
  if (!match) {
    return null;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6]);
  if (!isRealDate(year, month, day) || hour > 23 || minute > 59 || second > 59) {
    return null;
  }
  const fraction = (match[7] ?? ".").slice(1).padEnd(6, "0");
  let utc =
    BigInt(daysFromCivil(year, month, day)) * BigInt("86400000000") +
    BigInt(hour) * BigInt("3600000000") +
    BigInt(minute) * BigInt("60000000") +
    BigInt(second) * BigInt("1000000") +
    BigInt(fraction);
  const zone = match[8];
  if (zone !== "Z") {
    const sign = zone.startsWith("-") ? BigInt(-1) : BigInt(1);
    const zoneHour = Number(zone.slice(1, 3));
    const zoneMinute = Number(zone.slice(4, 6));
    if (zoneHour > 23 || zoneMinute > 59) {
      return null;
    }
    utc -= sign * (BigInt(zoneHour) * BigInt("3600000000") + BigInt(zoneMinute) * BigInt("60000000"));
  }
  return utc;
}

function isRealDate(year: number, month: number, day: number): boolean {
  if (month < 1 || month > 12 || day < 1) {
    return false;
  }
  const lengths = [0, 31, leapYear(year) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return day <= lengths[month];
}

function leapYear(year: number): boolean {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function daysFromCivil(year: number, month: number, day: number): number {
  let normalizedYear = year;
  if (month <= 2) {
    normalizedYear -= 1;
  }
  const era = Math.floor(normalizedYear / 400);
  const yearOfEra = normalizedYear - era * 400;
  const dayOfYear = Math.floor((153 * (month > 2 ? month - 3 : month + 9) + 2) / 5) + day - 1;
  const dayOfEra = yearOfEra * 365 + Math.floor(yearOfEra / 4) - Math.floor(yearOfEra / 100) + dayOfYear;
  return era * 146097 + dayOfEra - 719468;
}

function toMilli(value: string): bigint | null {
  if (!DECIMAL.test(value)) {
    return null;
  }
  const [whole, fraction = ""] = value.split(".");
  return BigInt(whole) * BigInt(1000) + BigInt((fraction + "000").slice(0, 3));
}

function roundHalfUp(numerator: bigint, denominator: bigint): bigint {
  const quotient = numerator / denominator;
  const remainder = numerator % denominator;
  if (remainder * BigInt(2) >= denominator) {
    return quotient + BigInt(1);
  }
  return quotient;
}
