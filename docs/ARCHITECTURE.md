# Architecture

BijliBachat AI is a two-part application in one repository. The browser presents the household view. The Python API will own tariff and money calculations. This version builds the boundary and does not implement those calculations.

## Frontend

The frontend is a Next.js App Router application in `frontend/`.

- `src/app` defines routes. `/` redirects to `/dashboard`. Overview is a complete sample screen. Cliff Guard, Bill Auditor, Meter Readings, Action Plan, History, and Settings are reachable. Settings can change the theme on this device. The other routes explain what they will do and state that the work is not available yet.
- `src/lib/navigation.ts` is the only route list. The desktop sidebar, mobile tabs, and More sheet read it. Journey groups are Understand, Prevent, Optimize, and Measure. Settings stays with the sample profile, not inside those groups.
- `src/components/ui` is a small local component set. There is no third-party component kit.
- `src/components/layout` is the shared shell: sidebar, header, mobile navigation, page container, and the API status line. Pages do not repeat the shell. The sidebar can collapse to icons. That choice is stored on this device, the same way as the theme.
- `src/features/overview/demo-data.ts` holds the sample figures. Components render those authored values. They do not derive a bill, a slab, or a saving.
- A short consistency check in that file fails the build if the authored unit total and the daily series drift apart. That check is a content guard, not a billing engine.

The root layout stays statically renderable. Theme preference and the collapsed sidebar are applied by small inline scripts that read `localStorage` before paint, then by client controls. The server does not read those choices, so the layout does not depend on the request.

`NEXT_PUBLIC_API_URL` is the only frontend environment value. The service-status footer calls `GET /api/health` and checks the JSON shape before showing it. A missing URL, a network failure, or an unexpected body is shown as unavailable.

## Backend

The backend is a FastAPI application in `backend/`. `create_app()` builds the process, stores settings on `app.state`, and attaches CORS. Origins must be explicit `http` or `https` URLs. A wildcard is a startup error. Settings do not read API keys. None are used.

`GET /api/health` is unchanged. `status: "ok"` means the process handled the request. Firebase, Gemini, and tariff configuration stay `not_configured`. The frontend checks that JSON shape before showing it.

### Responsibilities

- `app/api/` receives HTTP, returns the health report, and maps an unexpected failure to the public error body. Routes do not calculate a bill and do not open a database.
- `app/core/` holds environment settings.
- `app/schemas/` holds the contracts: health, household profile, meter checkpoint, trust status, decimal amounts, and `ErrorResponse`.
- `app/services/` holds application logic. The health report lives here. Future tariff and money calculations belong here too, and they must not import a database client.
- `tests/` covers the health route, CORS, settings, and the new contracts.

There is no `repositories/` package and no `integrations/` package yet. Empty folders would look like storage that does not exist.

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
- Gemini, when a stage asks for it, goes in `app/integrations/gemini/`. It may extract text. It does not calculate money, and it does not overwrite a Python result.
- Dated tariff files and the calculation engine belong to later stages. They are not represented by sample rates in this code.

No database client, queue, or external SDK is created.

## Planned data flow

Later stages should keep this direction:

1. A person enters a meter checkpoint, or confirms fields extracted from a photo.
2. The API validates that input.
3. Python loads a verified, dated tariff file and calculates units, slab position, and rupees.
4. The response includes each important number with its trust status.
5. The interface renders those values. It does not recompute them.
6. If a bill and the household record disagree, the API can return a possible mismatch. It does not label the household.

Gemini, once added, may return text and extracted fields. Uncertain fields stay unconfirmed until a person accepts them. Gemini output is not allowed to overwrite a Python result.

## What this version deliberately leaves open

- The browser still shows a labeled sample household. The API does not register or store one.
- There is no tariff file and no rate table. The health check records that none is loaded.
- Household and meter contracts are validated in tests. They are not HTTP endpoints.
- There is no shared generated client. The frontend type for the health payload is hand-written and checked at runtime. A generator can wait until the API has more than one resource.
- The demo trust chips use lowercase keys (`verified`, `calculated`, and the rest). The API contract uses the labels `Verified`, `Calculated`, `Extracted`, `Estimated`, and `Unavailable`. The chips are local sample UI. They do not read the API contract yet.

## Trust boundaries

| Concern | Owner in this version | Later owner |
| --- | --- | --- |
| Layout, theme, sample copy | Frontend | Frontend |
| Process health | FastAPI | FastAPI |
| Tariff rates and bill maths | Not implemented. Python services will own them | Python only, in `app/services/` |
| OCR and explanation | Not implemented | Gemini, in `app/integrations/gemini/`, with human confirmation |
| Stored households and photos | Not implemented. Contracts exist; nothing is saved | Firestore and Storage, behind `app/repositories/` |
