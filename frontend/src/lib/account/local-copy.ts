/**
 * A one-time copy of records already in this browser.
 * Theme, language, budgets, and scenario drafts stay on the device.
 * The copy does not delete local records and is not continuous synchronization.
 */

export type CopyPlan = {
  continuousSynchronization: false;
  removesLocalRecords: false;
  counts: { collection: string; count: number }[];
  rejected: { collection: string; reason: string }[];
  payload: Record<string, unknown[]>;
};

type StorageLike = {
  getItem(key: string): string | null;
};

export const DEVICE_RECORD_KEYS = [
  "bijlibachat.meter-ledger.v1",
  "bijlibachat.meter-household.v1",
  "bijlibachat.budget.v1",
  "bijlibachat.prediction-cycle.v1",
  "bijlibachat.appliances.v1",
  "bijlibachat.appliance-scenario.v1",
  "bijlibachat.history-cycles.v1",
  "bijlibachat.forecast-snapshots.v1",
  "bijlibachat.history-baselines.v1",
] as const;

const METER_KEY = DEVICE_RECORD_KEYS[0];
const APPLIANCE_KEY = "bijlibachat.appliances.v1";
const CYCLE_KEY = "bijlibachat.history-cycles.v1";
const SNAPSHOT_KEY = "bijlibachat.forecast-snapshots.v1";
const BASELINE_KEY = "bijlibachat.history-baselines.v1";

type RemovableStorage = {
  removeItem(key: string): void;
};

/** Remove household records kept in this browser. Theme, language, and the sidebar stay. */
export function clearDeviceRecords(storage: RemovableStorage): readonly string[] {
  for (const key of DEVICE_RECORD_KEYS) {
    storage.removeItem(key);
  }
  return DEVICE_RECORD_KEYS;
}

const allowedTrust = new Set(["Calculated", "Extracted", "Estimated"]);

export function recordsFromLocal(storage: StorageLike): CopyPlan {
  const rejected: CopyPlan["rejected"] = [];
  const meter = takeRecords(storage, METER_KEY, "meter_checkpoints", rejected, isMeter);
  const appliances = takeRecords(storage, APPLIANCE_KEY, "appliances", rejected, isAppliance);
  const cycles = takeRecords(storage, CYCLE_KEY, "history_cycles", rejected, isCycle);
  const snapshots = takeRecords(storage, SNAPSHOT_KEY, "forecast_snapshots", rejected, isSnapshot);
  const baselines = takeRecords(storage, BASELINE_KEY, "history_baselines", rejected, isBaseline);
  const payload = {
    meter_checkpoints: meter,
    appliances,
    history_cycles: cycles,
    forecast_snapshots: snapshots,
    history_baselines: baselines,
  };
  return {
    continuousSynchronization: false,
    removesLocalRecords: false,
    counts: Object.entries(payload).map(([collection, records]) => ({
      collection,
      count: records.length,
    })),
    rejected,
    payload,
  };
}

function takeRecords(
  storage: StorageLike,
  key: string,
  collection: string,
  rejected: CopyPlan["rejected"],
  accept: (value: unknown) => Record<string, unknown> | null,
): Record<string, unknown>[] {
  const parsed = readArray(storage.getItem(key));
  if (parsed === null) {
    if (storage.getItem(key)) {
      rejected.push({ collection, reason: "The saved list could not be read." });
    }
    return [];
  }
  const accepted: Record<string, unknown>[] = [];
  for (const item of parsed) {
    const record = accept(item);
    if (record) {
      accepted.push(record);
    } else {
      rejected.push({ collection, reason: "The record did not match the saved shape." });
    }
  }
  return accepted;
}

function readArray(raw: string | null): unknown[] | null {
  if (!raw) {
    return [];
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

function isMeter(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value) || typeof value.id !== "string") {
    return null;
  }
  if (!allowedTrust.has(String(value.trust_status)) || value.trust_status === "Verified") {
    return null;
  }
  return { ...value, confirmation_state: "confirmed" };
}

function isAppliance(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value) || typeof value.id !== "string" || typeof value.name !== "string") {
    return null;
  }
  return value;
}

function isCycle(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value) || value.trust_status !== "Calculated" || typeof value.id !== "string") {
    return null;
  }
  return value;
}

function isSnapshot(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value) || value.trust_status !== "Estimated" || value.method !== "checkpoint-pace-v1") {
    return null;
  }
  return value;
}

function isBaseline(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value) || typeof value.cycle_id !== "string" || typeof value.target_kwh !== "string") {
    return null;
  }
  return value;
}
