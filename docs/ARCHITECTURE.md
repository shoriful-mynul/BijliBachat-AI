# Architecture

BijliBachat AI is a two-part application in one repository. The browser presents the household view. The Python API owns tariff and money calculations. Bill Auditor calls the tariff API after a person confirms a bill. The sample overview does not.

## Frontend

The frontend is a Next.js App Router application in `frontend/`.

- `src/app` defines routes. `/` redirects to `/dashboard`. Overview is a complete sample screen. Bill Auditor uploads a bill, reviews an extraction, and shows an audit. Settings can change the theme on this device. Cliff Guard, Meter Readings, Action Plan, and History explain what they will do and state that the work is not available yet.
- `src/lib/navigation.ts` is the only route list. The desktop sidebar, mobile tabs, and More sheet read it. Journey groups are Understand, Prevent, Optimize, and Measure. Settings stays with the sample profile, not inside those groups.
- `src/components/ui` is a small local component set. There is no third-party component kit.
- `src/components/layout` is the shared shell: sidebar, header, mobile navigation, page container, and the API status line. Pages do not repeat the shell. The sidebar can collapse to icons. That choice is stored on this device, the same way as the theme.
- `src/features/overview/demo-data.ts` holds the sample figures. Components render those authored values. They do not derive a bill, a slab, or a saving.
- `src/features/bill-auditor/` is the review screen. It sends files and confirmed values to the API. It does not calculate a tariff.
- A short consistency check in that file fails the build if the authored unit total and the daily series drift apart. That check is a content guard, not a billing engine.

The root layout stays statically renderable. Theme preference and the collapsed sidebar are applied by small inline scripts that read `localStorage` before paint, then by client controls. The server does not read those choices, so the layout does not depend on the request.

`NEXT_PUBLIC_API_URL` is the only frontend environment value. The service-status footer calls `GET /api/health` and checks the JSON shape before showing it. A missing URL, a network failure, or an unexpected body is shown as unavailable.

## Backend

The backend is a FastAPI application in `backend/`. `create_app()` builds the process, stores settings on `app.state`, and attaches CORS. Origins must be explicit `http` or `https` URLs. A wildcard is a startup error. The optional Gemini key is a backend setting. It is not required to start the API, and it is not returned by any route.

`GET /api/health` keeps its shape. `status: "ok"` means the process handled the request. Firebase and tariff configuration stay `not_configured`. The Gemini check also stays `not_configured`: this route does not call Gemini. When a key is set, the Gemini detail says so and the top-level detail still says Firebase and a complete payable tariff are not connected. The tariff check stays `not_configured` because the packaged schedules do not contain a complete payable bill. The frontend checks that JSON shape before showing it.

### Responsibilities

- `app/api/` receives HTTP, returns the health report, tariff responses, and bill responses, and maps an unexpected failure to the public error body. Routes validate input and call services. They do not contain a tariff formula and they do not open a database.
- `app/core/` holds environment settings, including the optional Gemini key and model.
- `app/schemas/` holds the contracts: health, household profile, meter checkpoint, trust status, decimal amounts, tariff requests and responses, bill extraction and audit, and `ErrorResponse`.
- `app/tariffs/` holds dated JSON schedules, the availability notes for schedules that are not loaded, and the loader that rejects overlap, invalid bands, and synthetic production files.
- `app/services/` holds application logic. The health report, `tariff_engine.py`, bill file checks, extraction parsing, the audit comparison, and the complaint template live here. The engine does not import a database client.
- `app/integrations/gemini/` calls the Gemini SDK. Tests replace that client. Nothing else imports it to calculate money.
- `tests/` covers health, CORS, settings, the data contracts, tariff files, tariff calculations, and bill extraction with a fake Gemini client. Synthetic rates live in the tests and are labeled as fixtures.

There is no `repositories/` package. Bills are not stored.

### Contracts

Household and meter models describe records a later stage can store. No route accepts them, and nothing writes them.

- Identifiers are UUIDs.
- Timestamps must include a timezone. The models store them as UTC.
- Kilowatt-hour and rupee amounts are `Decimal`. JSON sends them as strings. Binary floats and scientific notation are rejected. A fractional JSON number is a float after parsing, so it is rejected too. Whole numbers are accepted.
- Trust status is exactly `Verified`, `Calculated`, `Extracted`, `Estimated`, or `Unavailable`.
- A household has a display name, an open provider code, an optional city or service area, and two timestamps. It has no street address, national ID, meter account number, or protected-consumer flag. The provider code is not a fixed list of companies.
- A meter checkpoint has a register value, a timestamp, `manual` or `photo`, and an explicit confirmation state: `pending_confirmation` or `confirmed`. Nothing fills that state in. A photo extraction is not confirmed unless the caller says so. The optional source is a short label, not a file or an OCR payload.
- `ErrorResponse` is `code` plus `message`. Unexpected server errors use it and omit the exception text. FastAPI field errors stay a `detail` list, with a location and a message for each field.

### Where later integrations go

- Persistence, when a stage asks for it, goes in `app/repositories/`. Services call that boundary. Routes do not.
- Firebase Authentication, Cloud Firestore, and Firebase Storage, when a stage asks for them, go in `app/integrations/firebase/`. The app does not import or initialize them now.
- Gemini bill extraction lives in `app/integrations/gemini/`. It may extract text. It does not calculate money, and it does not overwrite a Python result. Meter-photo OCR is not implemented.
- Dated tariff files and the calculation engine live in `app/tariffs/` and `app/services/tariff_engine.py`. The format, the IESCO rows that were verified, and the companies that remain unavailable are recorded in [TARIFF_ENGINE.md](TARIFF_ENGINE.md). The bill comparison rules are in [BILL_AUDITOR.md](BILL_AUDITOR.md).

No database client or queue is created. The Gemini SDK is imported only when an extraction runs.

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

- The browser still shows a labeled sample household. The API does not register or store one, and the overview does not call the tariff API.
- IESCO residential energy and fixed-charge rows from the company's February 2026 tariff guide are packaged. GST, fuel price adjustment, electricity duty, and TV fee are not in that guide, so no production request returns a payable total. LESCO, K-Electric, and IESCO protected residential consumption have no calculable file. The health check stays `not_configured` for that reason.
- Household and meter contracts are validated in tests. They are not HTTP endpoints.
- There is no shared generated client. The frontend type for the health payload is hand-written and checked at runtime. A generator can wait until the API has more than one resource.
- The demo trust chips use lowercase keys (`verified`, `calculated`, and the rest). The API contract uses the labels `Verified`, `Calculated`, `Extracted`, `Estimated`, and `Unavailable`. The chips are local sample UI. They do not read the API contract yet.

## Trust boundaries

| Concern | Owner in this version | Later owner |
| --- | --- | --- |
| Layout, theme, sample copy | Frontend | Frontend |
| Process health | FastAPI | FastAPI |
| Tariff rates and bill maths | Python, in `app/services/tariff_engine.py`, from dated files only. No production payable total yet | Python only |
| Bill OCR | Gemini extraction in `app/integrations/gemini/`, then a person confirms the form | Same boundary. Meter-photo OCR is still not implemented |
| Stored households and photos | Not implemented. Contracts exist; nothing is saved | Firestore and Storage, behind `app/repositories/` |
