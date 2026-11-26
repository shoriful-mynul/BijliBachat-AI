import assert from "node:assert/strict";
import test from "node:test";
import { en } from "../i18n/messages.ts";
import { clearDeviceRecords, recordsFromLocal } from "./local-copy.ts";
import { readPublicFirebaseConfig } from "../firebase/public-config.ts";
import { sessionView, signInOutcome } from "../firebase/session.ts";

const completeConfig = {
  NEXT_PUBLIC_FIREBASE_API_KEY: "public-key",
  NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: "demo.firebaseapp.com",
  NEXT_PUBLIC_FIREBASE_PROJECT_ID: "demo",
  NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET: "demo.appspot.com",
  NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID: "123",
  NEXT_PUBLIC_FIREBASE_APP_ID: "1:123:web:abc",
};

test("firebase configuration is absent unless every public field is set", () => {
  assert.equal(readPublicFirebaseConfig({}), null);
  assert.equal(readPublicFirebaseConfig({ ...completeConfig, NEXT_PUBLIC_FIREBASE_APP_ID: "  " }), null);
  assert.deepEqual(readPublicFirebaseConfig(completeConfig)?.projectId, "demo");
});

test("local mode cannot report a successful sign-in", () => {
  assert.deepEqual(signInOutcome(false, null), { ok: false, reason: "unavailable" });
  assert.deepEqual(sessionView(false, "signed-in", "person@example.com"), { mode: "local" });
});

test("cloud sign-in states stay distinct from a rejected session", () => {
  assert.deepEqual(sessionView(true, "loading", null), { mode: "cloud", phase: "loading" });
  assert.deepEqual(signInOutcome(true, null), { ok: true });
  assert.deepEqual(signInOutcome(true, "auth/invalid-credential"), { ok: false, reason: "invalid" });
  assert.deepEqual(signInOutcome(true, "auth/user-token-expired"), { ok: false, reason: "rejected" });
  assert.equal(sessionView(true, "signed-in", "person@example.com").mode, "cloud");
});

test("a local copy does not claim synchronization or keep a verified draft", () => {
  const storage = new Map([
    [
      "bijlibachat.meter-ledger.v1",
      JSON.stringify([
        {
          id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          household_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
          register_kwh: "10.000",
          read_at: "2026-01-01T00:00:00Z",
          meter_reference: "MTR-1001",
          capture_method: "manual",
          trust_status: "Calculated",
          warnings: [],
        },
        {
          id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          trust_status: "Verified",
        },
      ]),
    ],
    ["bb-theme", "dark"],
    ["bijlibachat.language.v1", "ur"],
  ]);
  const plan = recordsFromLocal({
    getItem: (key) => storage.get(key) ?? null,
  });

  assert.equal(plan.continuousSynchronization, false);
  assert.equal(plan.removesLocalRecords, false);
  assert.equal(plan.payload.meter_checkpoints.length, 1);
  assert.equal(plan.payload.meter_checkpoints[0].confirmation_state, "confirmed");
  assert.equal(plan.rejected.length, 1);
  assert.equal(JSON.stringify(plan.payload).includes("bb-theme"), false);
  assert.equal(JSON.stringify(plan.payload).includes("token"), false);
  assert.match(en["account.copyResult"], /not synchronization/i);
  assert.match(en["account.localBody"], /not synchronized/i);
  assert.doesNotMatch(en["account.copyResult"], /successfully synchronized/i);
});

test("clearing this browser does not remove theme, language, or claim a cloud delete", () => {
  const storage = new Map([
    ["bijlibachat.meter-ledger.v1", "[]"],
    ["bijlibachat.appliances.v1", "[]"],
    ["bb-theme", "dark"],
    ["bijlibachat.language.v1", "\"ur\""],
    ["bb-sidebar", "collapsed"],
  ]);
  clearDeviceRecords({
    removeItem: (key) => storage.delete(key),
  });
  assert.equal(storage.has("bijlibachat.meter-ledger.v1"), false);
  assert.equal(storage.get("bb-theme"), "dark");
  assert.equal(storage.get("bijlibachat.language.v1"), "\"ur\"");
  assert.equal(storage.get("bb-sidebar"), "collapsed");
  assert.match(en["account.resetDone"], /not removed/i);
});
