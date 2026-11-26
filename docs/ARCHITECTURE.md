# Architecture

BijliBachat AI is a two-part application in one repository. The browser presents the household view. The Python API owns tariff and money calculations. Bill Auditor calls the tariff API after a person confirms a bill. The sample overview does not.

## Frontend

The frontend is a Next.js App Router application in `frontend/`.

- `src/app` defines routes. `/` redirects to `/dashboard`. Overview keeps its labeled sample cards and adds a forecast summary from checkpoints on this device. Bill Auditor, Cliff Guard, Meter Readings, Forecast, Action Plan, and History are implemented. Settings can change the language and the theme on this device, and shows whether sign-in is configured.
- `src/lib/navigation.ts` is the only route list. The desktop sidebar, mobile tabs, and More sheet read it. Journey groups are Understand, Prevent, Optimize, and Measure. Settings stays with the sample profile, not inside those groups.
- `src/components/ui` is a small local component set. There is no third-party component kit.
- `src/components/layout` is the shared shell: sidebar, header, mobile navigation, page container, and the API status line. Pages do not repeat the shell. The sidebar can collapse to icons. That choice is stored on this device, the same way as the theme.
- `src/features/overview/demo-data.ts` holds the sample figures. Components render those authored values. They do not derive a bill, a slab, or a saving.
- `src/features/bill-auditor/` is the review screen. It sends files and confirmed values to the API. It does not calculate a tariff.
- `src/features/meter/` records checkpoints and shows Cliff Guard. Confirmed readings stay in this browser. The pages do not calculate consumption.
- `src/features/prediction/` asks the API for a cycle forecast and keeps a household budget in this browser. It does not price a bill.
- `src/features/appliances/` keeps appliance records in this browser and asks the API for consumption and scenarios. It does not price a saving.
- `src/features/history/` keeps measured cycles, saved forecasts, and kWh targets in this browser. It asks the API to compare them and does not price a saving.
- `src/lib/i18n/` holds the English and Urdu dictionaries and the language storage key `bijlibachat.language.v1`. Components call one translation function. Pages are not copied per language. Urdu sets `lang="ur"` and `dir="rtl"`. Chart plots stay left-to-right. The details are in [LOCALIZATION_ACCESSIBILITY.md](LOCALIZATION_ACCESSIBILITY.md).
- A short consistency check in that file fails the build if the authored unit total and the daily series drift apart. That check is a content guard, not a billing engine.

The root layout stays statically renderable. Theme, language, and the collapsed sidebar are applied by small inline scripts that read `localStorage` before paint, then by client controls. The server does not read those choices, so the layout does not depend on the request. Language does not write the theme key.

`NEXT_PUBLIC_API_URL` is required for API calls. The public `NEXT_PUBLIC_FIREBASE_*` values are optional. If any one is missing, the browser stays in local/demo mode and does not offer a successful sign-in. The service-status footer calls `GET /api/health` and checks the JSON shape before showing it. A missing URL, a network failure, or an unexpected body is shown as unavailable. Account calls go to `/api/account` and attach a Firebase ID token only for that request. The token is not written into household records.

## Backend

The backend is a FastAPI application in `backend/`. `create_app()` builds the process, stores settings on `app.state`, and attaches CORS. Origins must be explicit `http` or `https` URLs. A wildcard is a startup error. The optional Gemini key and the optional Firebase Admin credentials are backend settings. Neither is required to start the API, and neither is returned by any route.

`GET /api/health` keeps its shape. `status: "ok"` means the process handled the request. The Firebase check stays `not_configured` because this route does not call Firebase. Without Admin credentials its detail says Firebase is not connected. With credentials, the detail says they are present and that the check did not call Firebase. The Gemini check also stays `not_configured`: this route does not call Gemini. When a key is set, the Gemini detail says so. A complete payable tariff stays not connected. The tariff check stays `not_configured` because the packaged schedules do not contain a complete payable bill. The frontend checks that JSON shape before showing it.

### Responsibilities

- `app/api/` receives HTTP, returns the health report, tariff responses, bill responses, and account responses, and maps an unexpected failure to the public error body. Routes validate input and call services. They do not contain a tariff formula. Account routes are the only ones that write user records, and only after a verified token.
- `app/core/` holds environment settings, including the optional Gemini key and the optional Firebase Admin settings.
- `app/schemas/` holds the contracts: health, household profile, meter checkpoint, trust status, decimal amounts, tariff requests and responses, bill extraction and audit, and `ErrorResponse`.
- `app/tariffs/` holds dated JSON schedules, the availability notes for schedules that are not loaded, and the loader that rejects overlap, invalid bands, and synthetic production files.
- `app/services/` holds application logic. The health report, `tariff_engine.py`, bill checks, meter validation, Cliff Guard, the consumption forecast, appliance scenarios, and history comparisons live here. The engine does not import a database client.
- `app/repositories/meter_ledger.py` is the storage boundary for the meter route. That route still retains nothing. `user_records.py` and `user_files.py` store confirmed account data when Firebase is configured. Tests inject in-memory versions of those stores.
- `app/auth/` verifies Firebase ID tokens with the Admin SDK. A missing configuration does not treat the caller as a signed-in user. Tests use `FakeTokenVerifier`.
- `app/integrations/gemini/` calls the Gemini SDK for bill documents and meter photos. Tests replace that client. Nothing else imports it to calculate money.
- `tests/` covers health, CORS, settings, the data contracts, tariff files, tariff calculations, bill extraction with a fake Gemini client, and account ownership with a fake token verifier. Synthetic rates live in the tests and are labeled as fixtures.

The meter route and the bill extraction route do not retain uploads. Account routes can retain a confirmed record or a file after an explicit choice, and only for the UID in the verified token.

### Contracts

Household and meter models describe records the account API can store after validation. Calculation routes still do not write them.

- Identifiers are UUIDs.
- Timestamps must include a timezone. The models store them as UTC.
- Kilowatt-hour and rupee amounts are `Decimal`. JSON sends them as strings. Binary floats and scientific notation are rejected. A fractional JSON number is a float after parsing, so it is rejected too. Whole numbers are accepted.
- Trust status is exactly `Verified`, `Calculated`, `Extracted`, `Estimated`, or `Unavailable`.
- A household has a display name, an open provider code, an optional city or service area, and two timestamps. It has no street address, national ID, meter account number, or protected-consumer flag. The provider code is not a fixed list of companies.
- A meter checkpoint has a register value, a timestamp, `manual` or `photo`, and an explicit confirmation state: `pending_confirmation` or `confirmed`. Nothing fills that state in. A photo extraction is not confirmed unless the caller says so. The optional source is a short label, not a file or an OCR payload.
- `ErrorResponse` is `code` plus `message`. Unexpected server errors use it and omit the exception text. FastAPI field errors stay a `detail` list, with a location and a message for each field.

### Where later integrations go

- Account persistence goes through `app/repositories/`. Calculation services do not open Firestore.
- Firebase Admin is initialized only when a token must be verified or a configured store is used. The client SDK is loaded in the browser only when every public Firebase setting is present. Security rules in `firebase/` are a second layer for direct client access. The Admin SDK bypasses those rules, so the API checks the token as well.
- Gemini bill extraction and meter-photo extraction live in `app/integrations/gemini/`. They may extract text. They do not calculate money or consumption, and they do not overwrite a Python result.
- Dated tariff files and the calculation engine live in `app/tariffs/` and `app/services/tariff_engine.py`. The format, the IESCO rows that were verified, and the companies that remain unavailable are recorded in [TARIFF_ENGINE.md](TARIFF_ENGINE.md). The bill comparison rules are in [BILL_AUDITOR.md](BILL_AUDITOR.md).

No queue is created. The Gemini SDK is imported only when an extraction runs. The Firebase Admin SDK is imported only when account credentials are configured and a token or store operation needs it.

## Planned data flow

Later stages should keep this direction:

1. A person enters a meter checkpoint, or confirms fields extracted from a photo.
2. The API validates that input.
3. Python loads the verified, dated tariff file for that company, category, and billing date, and calculates only the components that file verifies.
4. The response includes each important number with its trust status.
5. The interface renders those values. It does not recompute them.
6. If a bill and the household record disagree, the API can return a possible mismatch. It does not label the household.

Gemini returns extracted fields. Uncertain fields stay unconfirmed until a person submits the audit form. Gemini output is not allowed to overwrite a Python result. The audit compares confirmed components only, and it does not treat a partial tariff as a payable total.

## What this version deliberately leaves open

- The browser still shows a labeled sample household on the overview. That page does not call the tariff API. A household profile can be saved from Settings only after sign-in, and only when the API has Firebase credentials.
- IESCO residential energy and fixed-charge rows from the company's February 2026 tariff guide are packaged. GST, fuel price adjustment, electricity duty, and TV fee are not in that guide, so no production request returns a payable total. LESCO, K-Electric, and IESCO protected residential consumption have no calculable file. The health check stays `not_configured` for that reason.
- Household and meter contracts are validated before an account write. The calculation endpoints still accept the records needed for one calculation and do not store them.
- There is no shared generated client. The frontend type for the health payload is hand-written and checked at runtime. A generator can wait until the API has more than one resource.
- The demo trust chips use lowercase keys (`verified`, `calculated`, and the rest). The API contract uses the labels `Verified`, `Calculated`, `Extracted`, `Estimated`, and `Unavailable`. The chips are local sample UI. They do not read the API contract yet.

## Trust boundaries

| Concern | Owner in this version | Later owner |
| --- | --- | --- |
| Layout, theme, sample copy | Frontend | Frontend |
| Process health | FastAPI | FastAPI |
| Tariff rates and bill maths | Python, in `app/services/tariff_engine.py`, from dated files only. No production payable total yet | Python only |
| Bill and meter OCR | Gemini extraction in `app/integrations/gemini/`, then a person confirms the form | Same boundary. Originals are kept only after an explicit signed-in choice |
| Stored households and files | Firestore and Storage behind `app/repositories/`, when Admin credentials and a bucket are configured. Otherwise the browser keeps its own records | Same boundary |
