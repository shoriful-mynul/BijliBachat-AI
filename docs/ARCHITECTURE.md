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

The backend is a FastAPI application in `backend/`.

- `app/main.py` builds the app, stores settings on `app.state`, and attaches CORS.
- `app/core/config.py` reads `APP_ENV` and `CORS_ORIGINS`. Origins must be explicit `http` or `https` URLs. A wildcard is a startup error.
- `app/api/routes/health.py` exposes `GET /api/health`.
- `app/services/health.py` builds a truthful report: the process is running, and Firebase, Gemini, and tariff configuration are `not_configured`.
- `app/schemas/health.py` is the response contract.

No database, queue, or external client is created.

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

- There is no household identity beyond a labeled sample profile.
- There is no tariff file format yet. The health check records that none is loaded, so a later stage can add `backend` configuration without pretending a rule already exists.
- There is no shared generated client. The frontend type for the health payload is hand-written and checked at runtime. A generator can wait until the API has more than one resource.

## Trust boundaries

| Concern | Owner in this version | Later owner |
| --- | --- | --- |
| Layout, theme, sample copy | Frontend | Frontend |
| Process health | FastAPI | FastAPI |
| Tariff rates and bill maths | Not implemented | Python only |
| OCR and explanation | Not implemented | Gemini, with human confirmation |
| Stored households | Not implemented | Firestore, after authentication |
