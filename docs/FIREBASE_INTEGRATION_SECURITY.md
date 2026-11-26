# Firebase integration and security

Part 11 connects optional Firebase Authentication, Cloud Firestore, and Firebase Storage without taking calculation authority away from Python. When the settings are empty, the app stays in local/demo mode. This is not a certified security audit, and it is not continuous synchronization.

## Operating modes

**Local/demo mode.** The browser is in this mode when any public `NEXT_PUBLIC_FIREBASE_*` value is missing. Settings says records stay in this browser, that they are not backed up, and that sign-in is not available. The sign-in form is not shown, so the screen cannot report a successful sign-in. Existing `localStorage` keys are left in place.

**API without Admin credentials.** `POST` and `PUT` under `/api/account` return `503` with `Cloud accounts are not configured. Nothing was saved.` Health still reports the Firebase check as `not_configured`. Calculation routes keep working and still do not store the records they receive.

**Firebase-connected mode.** The browser loads email/password authentication only when every public client value is set. The API verifies the ID token only when `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, and `FIREBASE_PRIVATE_KEY` are all set. File retention also needs `FIREBASE_STORAGE_BUCKET`. A signed-in browser with an API that has no Admin credentials can sign in to Firebase and still receive an honest failure when a copy is attempted. A failed copy does not clear local records.

Health does not call Firebase. With credentials present, the Firebase check remains `not_configured` and its detail says the credentials are present and that the check did not call Firebase. A complete payable tariff stays unavailable.

## Authentication

The browser uses the Firebase client SDK with email and password. Passwords are not stored by this app. The ID token is attached to one account request as `Authorization: Bearer` and is not written into `bijlibachat.*` records, the page URL, or the visible interface.

The API dependency reads that header. `FirebaseTokenVerifier` calls `firebase_admin.auth.verify_id_token` with revocation checking. The UID is `decoded["uid"]`, and it must match `sub`. A missing header, a non-bearer scheme, an empty token, an invalid token, an expired token, and a revoked token return `401` with `ErrorResponse`. The message is `Sign in is required.` or `The session is no longer valid. Sign in again.` The token and the exception text are not returned. Tests use `FakeTokenVerifier`, which the settings builder never selects.

A body field named `owner_uid` or `uid` is rejected. The store writes `owner_uid` from the verified token.

## Public and protected routes

These stay public in both modes, because they do not read or write a household:

- `GET /api/health`
- `GET /api/tariffs`, `GET /api/tariffs/resolve`, and `POST /api/tariffs/calculations`
- Bill, meter, prediction, appliance, and history calculation routes. They still calculate from the posted body and do not retain it.

`/api/account/*` requires a verified token whenever a verifier and a record store are installed. In local mode those routes refuse the call instead of treating the anonymous caller as a user.

Bill and meter file checks are limited per client address by `EXTRACT_RATE_LIMIT_PER_MINUTE` (default 60, `0` disables the limit). The limiter is in-process. A limited call returns `429` with the existing `unavailable` error code. Ordinary tests stay under the default.

## Firestore collections

Documents live at `users/{uid}/{collection}/{id}`. The server sets `owner_uid` and does not accept it from the client. A second write of the same id returns `already_present` and does not replace the first document. That avoids overwriting a cloud record with an older local copy. It is not a sync engine: a newer local edit of the same id is reported as already present until the cloud record is deleted.

| Collection | What is accepted |
| --- | --- |
| `household` | `HouseholdProfile`. No address, national ID, or meter account number |
| `meter_checkpoints` | `confirmation_state` must be `confirmed`. Trust must be `Calculated`, `Extracted`, or `Estimated` |
| `bill_audits` | `confirmation` must be `user_confirmed`, wrapping a confirmed bill. An extraction draft is rejected |
| `appliances` | The existing appliance specification |
| `forecast_snapshots` | Trust `Estimated` and method `checkpoint-pace-v1` |
| `history_cycles` | Trust `Calculated`. Measured use, duration, and daily average must match the existing history helpers |
| `history_baselines` | A cycle id and a kWh target the household entered |
| `retained_files` | Written only by the file endpoint. Clients cannot import this collection |

Trust labels stay `Verified`, `Calculated`, `Extracted`, `Estimated`, and `Unavailable`. A checkpoint or snapshot cannot be promoted to `Verified`. Theme, language, the monthly budget, the open forecast form, and appliance scenario drafts stay on the device.

## Storage

Object names are `users/{uid}/retained/{fileId}`. The id is a UUID created by the server. The client does not choose the path. The response does not include a storage path or a public URL. A later download is `GET /api/account/files/{id}` and requires the owner's token.

The file is kept only when the form field `consent` is exactly `retain_in_account`. The default checkboxes on Bill Auditor and Meter Readings are off. Without sign-in, those screens say the file is checked and then discarded. Bytes are checked with the existing signature and 8 MB limit. A meter photo cannot be a PDF. The declared type must match the signature.

Deleting one file removes the object and its metadata. `DELETE /api/account/data` removes every document and retained object for that UID, then reports what remains. It does not delete the login unless `include_login=true`, and `complete` is true only when the requested steps succeeded. Browser records are never removed by these calls. Deleting a meter checkpoint or a bill audit does not delete a retained file; the file has its own delete action and is included in account-data deletion. That is the cleanup path, so a retained file is not left without a way to remove it.

If the bucket is unset, the file endpoint returns `503` and says the file was not kept. Extraction still works.

## Security rules

`firebase/firestore.rules` and `firebase/storage.rules` deny every path, then allow a user to read and write only under `users/{uid}` when `request.auth.uid == uid`. Creates and updates must keep `owner_uid` equal to that uid. Storage writes must be under 8 MB and one of JPEG, PNG, WebP, or PDF. There is no `allow read, write: if true`.

The Admin SDK bypasses these rules. The API check is the layer that protects server writes. The rules are the layer that protects a direct client SDK request. Both are required. `firebase.json` points the emulators at Auth `9099`, Firestore `8088`, and Storage `9199`.

This workspace has Java 21 and does not have the Firebase CLI emulator binaries installed. The automated tests therefore use the in-memory verifier, record store, and file store. They do not prove the rules engine itself. Loading the emulator and running a rules suite against those files is the remaining check for direct client access.

## Local records and migration

The copy on Settings lists counts from these keys before anything is sent:

- `bijlibachat.meter-ledger.v1`
- `bijlibachat.appliances.v1`
- `bijlibachat.history-cycles.v1`
- `bijlibachat.forecast-snapshots.v1`
- `bijlibachat.history-baselines.v1`

A meter checkpoint is sent with `confirmation_state: "confirmed"` because that list is only written after the person confirms a reading. `Verified` entries are left out and counted as rejected. The copy does not read `bb-theme`, `bijlibachat.language.v1`, the budget key, the prediction form, or the appliance scenario draft.

The API validates each item. A rejected item does not roll back the items that were accepted. Local keys are not deleted. The response sets `continuous_synchronization` and `local_records_removed` to false. The screen repeats that this is not synchronization.

## Account controls

Settings shows the mode, where records live, sign-in, sign-out, a household profile form, the copy list, a JSON download of the caller's documents, and account-data removal. Export and removal call the API with the current token. The download is the caller's records only. Removal reports leftover documents, files, or the login instead of claiming the account is gone.

The header menu shows the sample household until someone is signed in. After sign-in it shows the email. Overview figures stay labeled sample data.

## Environment variables

Placeholders live in `.env.example`. Do not commit `.env` or `frontend/.env.local`.

Backend, all optional: `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_STORAGE_BUCKET`, `EXTRACT_RATE_LIMIT_PER_MINUTE`.

Frontend, all optional and public: `NEXT_PUBLIC_FIREBASE_API_KEY`, `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`, `NEXT_PUBLIC_FIREBASE_PROJECT_ID`, `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`, `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID`, `NEXT_PUBLIC_FIREBASE_APP_ID`.

The private key is excluded from `repr(Settings)`. Account logs record a failure type, not the token, the file bytes, or the household document.

## What was tested

Backend, from `backend/` with the project virtualenv:

`pytest` — 223 passed.

That run includes the existing tariff, bill, meter, Cliff Guard, prediction, appliance, and history tests, plus `tests/test_account_security.py`. The new file covers a missing token, a malformed token, an invalid token, an expired token, a UID taken from the token, a rejected body UID, user A blocked from reading or deleting user B's record, a second write that does not replace the first, public health and tariff routes, a failed write that returns 503, an exception string kept out of the response, unconfirmed bill and meter drafts, a `Verified` checkpoint rejected, file consent and signature checks, cross-user file denial, a partial deletion report, the rules source text, the rate limiter, and a settings `repr` that hides the private key.

Frontend:

- `npm test` — 20 passed, including the account and session cases. Local mode cannot become a successful sign-in. A copy plan does not claim synchronization.
- `npm run lint` — passed.
- `npx tsc --noEmit` — passed.
- `npm run build` — passed.

No production Firebase project or service-account file was used.

Browser, with the public Firebase settings empty, so this is local/demo mode. Chrome headless loaded the dev server. The Playwright connector was unavailable. Pages had no horizontal overflow and no console or page errors.

- Settings at 1440×900, dark, English: “This browser only”, records are not backed up and are not synchronized, sign-in is not available. No sign-in success.
- Settings at 768×1024, dark, English: same account state.
- Settings at 390×844, light, Urdu: `lang=ur`, `dir=rtl`, the same local-mode statement in Urdu.
- Bill Auditor at 390×844, dark, English: files are checked and then discarded.
- Meter Readings at 1440×900, light, Urdu: right-to-left, and the file is not stored.
- Overview at 768×1024, light, English: the sample household remains sample data.

A signed-in Firebase session was not opened. This environment has no public Firebase client configuration, and the tests do not use a production project. The connected-mode screen states are covered by the session unit tests, not by a live Auth project.

## Known limits

- The rules files are checked as source. The emulator suite was not executed here, so direct client SDK denial still needs that run or a deployed ruleset.
- The Admin SDK bypasses rules. A bug in the API would not be stopped by the rules.
- The file-check limit is per process and per client address, not a global quota.
- The same record id is never updated. A changed local copy is not merged.
- Theme, language, budgets, and scenario drafts are not copied.
- Health does not prove that Firebase is reachable.
- Account deletion does not promise that a login is gone unless `login_deleted` is true.
- This is not a certified security audit or a WCAG certification.
- Tariff maths, forecast pace, Cliff Guard, appliance formulas, and history formulas were not changed. GST, fuel price adjustment, electricity duty, and the TV fee are still absent, so no payable total or PKR saving was added.
