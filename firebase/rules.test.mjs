/**
 * Rules tests against the Firebase emulator. They do not use a production project.
 * Run with `npm test` from firebase/, which starts the emulators first.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { assertFails, assertSucceeds, initializeTestEnvironment } from "@firebase/rules-unit-testing";
import { deleteDoc, doc, getDoc, setDoc, updateDoc } from "firebase/firestore";
import { deleteObject, getBytes, ref, uploadBytes } from "firebase/storage";

const rulesDir = new URL("./", import.meta.url);
const firestoreRules = readFileSync(new URL("firestore.rules", rulesDir), "utf8");
const storageRules = readFileSync(new URL("storage.rules", rulesDir), "utf8");
const jpeg = Uint8Array.from([0xff, 0xd8, 0xff, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xff, 0xd9]);

const testEnv = await initializeTestEnvironment({
  projectId: "demo-bijlibachat",
  firestore: { rules: firestoreRules, host: "127.0.0.1", port: 8088 },
  storage: { rules: storageRules, host: "127.0.0.1", port: 9199 },
});

test.after(async () => {
  await testEnv.cleanup();
});

test("firestore denies anonymous access, cross-user access, and a forged owner", async () => {
  const anon = testEnv.unauthenticatedContext().firestore();
  const aliceDb = testEnv.authenticatedContext("alice").firestore();
  const bobDb = testEnv.authenticatedContext("bob").firestore();
  const home = "users/alice/household/home";

  await assertFails(getDoc(doc(anon, home)));
  await assertFails(setDoc(doc(anon, home), { owner_uid: "alice", display_name: "Home" }));
  await assertFails(setDoc(doc(aliceDb, "users/bob/household/home"), { owner_uid: "bob" }));
  await assertFails(setDoc(doc(aliceDb, home), { owner_uid: "bob", display_name: "Home" }));
  await assertFails(getDoc(doc(aliceDb, "public/config")));
  await assertFails(getDoc(doc(aliceDb, "users/alice/household/home/secret/extra")));

  await assertSucceeds(setDoc(doc(aliceDb, home), { owner_uid: "alice", display_name: "Home" }));
  const own = await assertSucceeds(getDoc(doc(aliceDb, home)));
  assert.equal(own.data().display_name, "Home");
  await assertFails(getDoc(doc(bobDb, home)));
  await assertFails(updateDoc(doc(bobDb, home), { display_name: "Other" }));
  await assertFails(deleteDoc(doc(bobDb, home)));
  await assertFails(updateDoc(doc(aliceDb, home), { owner_uid: "bob" }));
  await assertSucceeds(updateDoc(doc(aliceDb, home), { owner_uid: "alice", display_name: "Later" }));
  await assertSucceeds(deleteDoc(doc(aliceDb, home)));
  const removed = await assertSucceeds(getDoc(doc(aliceDb, home)));
  assert.equal(removed.exists(), false);
});

test("storage denies other users, public paths, bad types, and files over 8 MB", async () => {
  const alice = testEnv.authenticatedContext("alice").storage();
  const bob = testEnv.authenticatedContext("bob").storage();
  const anon = testEnv.unauthenticatedContext().storage();
  const ownPath = "users/alice/retained/photo";
  const own = ref(alice, ownPath);

  await assertFails(uploadBytes(ref(anon, ownPath), jpeg, { contentType: "image/jpeg" }));
  await assertFails(uploadBytes(ref(bob, ownPath), jpeg, { contentType: "image/jpeg" }));
  await assertFails(uploadBytes(ref(alice, "users/alice/other/photo"), jpeg, { contentType: "image/jpeg" }));
  await assertFails(uploadBytes(ref(alice, "public/photo"), jpeg, { contentType: "image/jpeg" }));
  await assertFails(uploadBytes(own, jpeg, { contentType: "text/plain" }));
  await assertFails(uploadBytes(own, jpeg, { contentType: "image/gif" }));
  await assertFails(
    uploadBytes(own, new Uint8Array(8 * 1024 * 1024 + 1), { contentType: "image/jpeg" }),
  );

  await assertSucceeds(uploadBytes(own, jpeg, { contentType: "image/jpeg" }));
  await assertSucceeds(getBytes(own));
  await assertFails(getBytes(ref(bob, ownPath)));
  await assertFails(uploadBytes(ref(bob, ownPath), jpeg, { contentType: "image/png" }));
  await assertFails(deleteObject(ref(bob, ownPath)));
  await assertSucceeds(uploadBytes(own, jpeg, { contentType: "image/png" }));
  await assertSucceeds(deleteObject(own));
  await assert.rejects(getBytes(own), /does not exist/);
});
