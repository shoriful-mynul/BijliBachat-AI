import assert from "node:assert/strict";
import test from "node:test";
import { loadCycles, loadSnapshots } from "./store.ts";

const memory = new Map();

globalThis.localStorage = {
  getItem: (key) => memory.get(key) ?? null,
  setItem: (key, value) => {
    memory.set(key, value);
  },
  removeItem: (key) => {
    memory.delete(key);
  },
  clear: () => {
    memory.clear();
  },
  key: (index) => [...memory.keys()][index] ?? null,
  get length() {
    return memory.size;
  },
};

const START = "11111111-1111-4111-8111-111111111111";
const END = "22222222-2222-4222-8222-222222222222";
const CYCLE = "33333333-3333-4333-8333-333333333333";
const LATEST = "44444444-4444-4444-8444-444444444444";

function cycle(overrides = {}) {
  return {
    id: CYCLE,
    meter_reference: "MTR-1001",
    start_checkpoint_id: START,
    end_checkpoint_id: END,
    started_at: "2026-01-01T00:00:00Z",
    ended_at: "2026-01-31T00:00:00Z",
    start_register_kwh: "100.000",
    end_register_kwh: "250.000",
    actual_kwh: "150.000",
    duration_days: "30.000",
    average_daily_kwh: "5.000",
    trust_status: "Calculated",
    detail: "Measured use is 150.000 kWh.",
    ...overrides,
  };
}

function snapshot(overrides = {}) {
  return {
    id: CYCLE,
    meter_reference: "MTR-1001",
    created_at: "2026-11-08T00:00:00Z",
    cycle_started_on: "2026-11-01",
    cycle_ends_on: "2026-11-15",
    cycle_start_register_kwh: "100.000",
    latest_register_kwh: "170.000",
    latest_checkpoint_id: LATEST,
    projected_cycle_kwh: "140.000",
    reading_ids: [START, LATEST],
    assumptions: ["The pace is an estimate."],
    trust_status: "Estimated",
    method: "checkpoint-pace-v1",
    detail: "Saved forecast.",
    ...overrides,
  };
}

test("a consistent cycle is kept, including a half-up daily average", () => {
  memory.clear();
  const rounded = cycle({
    id: "55555555-5555-4555-8555-555555555555",
    started_at: "2026-04-01T00:00:00Z",
    ended_at: "2026-04-07T00:00:00Z",
    start_register_kwh: "0.000",
    end_register_kwh: "1.000",
    actual_kwh: "1.000",
    duration_days: "6.000",
    average_daily_kwh: "0.167",
  });
  memory.set("bijlibachat.history-cycles.v1", JSON.stringify([cycle(), rounded]));
  assert.equal(loadCycles().length, 2);
});

test("a cycle is dropped when its measured use does not match the registers", () => {
  memory.set("bijlibachat.history-cycles.v1", JSON.stringify([cycle({ actual_kwh: "149.000" })]));
  assert.deepEqual(loadCycles(), []);
});

test("a cycle is dropped when its duration does not match the timestamps", () => {
  memory.set("bijlibachat.history-cycles.v1", JSON.stringify([cycle({ duration_days: "29.000" })]));
  assert.deepEqual(loadCycles(), []);
});

test("a cycle is dropped when its daily average does not match the exact pace", () => {
  memory.set("bijlibachat.history-cycles.v1", JSON.stringify([cycle({ average_daily_kwh: "4.999" })]));
  assert.deepEqual(loadCycles(), []);
});

test("a snapshot is dropped for duplicate readings, a missing latest checkpoint, a lower register, or a false date", () => {
  const cases = [
    snapshot({ reading_ids: [START, START] }),
    snapshot({ latest_checkpoint_id: END, reading_ids: [START, LATEST] }),
    snapshot({ latest_register_kwh: "90.000" }),
    snapshot({ cycle_ends_on: "2026-02-31" }),
    snapshot({ created_at: "2026-02-31T00:00:00Z" }),
  ];
  for (const item of cases) {
    memory.set("bijlibachat.forecast-snapshots.v1", JSON.stringify([item]));
    assert.deepEqual(loadSnapshots(), [], JSON.stringify(item));
  }
});

test("a consistent snapshot is kept", () => {
  memory.set("bijlibachat.forecast-snapshots.v1", JSON.stringify([snapshot()]));
  assert.equal(loadSnapshots().length, 1);
});
