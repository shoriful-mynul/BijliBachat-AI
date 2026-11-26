# BijliBachat AI 2.0

Don't wait for the bill. Predict it, prevent avoidable overspending, and make better electricity decisions.

BijliBachat AI is a Pakistan-focused household electricity expense product for the Capital Youth Expo Hackathon, Track 3 — FinTech & Financial Inclusion. It is meant to feel like a careful consumer finance app: calm, specific, and honest about what is known.

## Core user journey

Understand → Predict → Prevent → Optimize → Measure

A household should be able to see its electricity position, anticipate the month's expense, stay clear of an avoidable slab change, choose a practical action, and look back at what happened. Parts 1 through 9 of that journey are implemented. The overview still uses clearly labeled sample data. A payable rupee total is not calculated, because the loaded tariffs omit GST, fuel price adjustment, electricity duty, and the TV fee.

## Technology stack

| Area | Choice |
| --- | --- |
| Frontend | Next.js 16 (App Router), React 19, TypeScript (strict), Tailwind CSS 4 |
| Charts and icons | Recharts 3, Lucide React |
| Backend | Python 3.11+, FastAPI, Pydantic v2, Uvicorn, google-genai 1.75 |
| Tests | pytest, FastAPI's `TestClient` |

Planned later, and not connected now: Firebase Authentication, Cloud Firestore, and Firebase Storage. Gemini is used for bill extraction and meter-photo extraction when `GEMINI_API_KEY` is set on the server. Confirmed meter checkpoints stay in the browser. The API does not keep them.

## Project structure

```
frontend/          Next.js application
  src/app/         Routes and the root layout
  src/components/  ui, layout, and dashboard components
  src/features/    Overview sample content, settings, Bill Auditor, meter checkpoints, the forecast, appliances, and history
  src/hooks/       Shared hooks
  src/lib/         Formatting, navigation, theme, health parsing
  src/styles/      Blue Hour tokens
  src/types/       Shared TypeScript types
backend/
  app/api/         HTTP routes and the public error response
  app/core/        Environment configuration
  app/schemas/     Health, household, meter, tariff, bill, trust, and error contracts
  app/services/    Health, tariff engine, bill audit, meter checks, Cliff Guard, the forecast, appliances, and history
  app/repositories/  Meter storage boundary. The API ledger retains nothing
  app/integrations/gemini/  Document extraction client
  app/tariffs/     Dated tariff files and availability notes
  tests/           Contract, tariff, bill, config, and API tests
docs/              Architecture, design system, roadmap
.cursor/rules/     Permanent engineering and design rules
```

The repository root is the product. There is no extra nested application folder.

## Development setup

Requirements: Node.js 20.9 or newer, npm, and Python 3.11 or newer.

```bash
cp .env.example backend/.env
cp .env.example frontend/.env.local
```

`frontend/.env.local` only needs the `NEXT_PUBLIC_API_URL` line. `backend/.env` needs `APP_ENV` and `CORS_ORIGINS`. `GEMINI_API_KEY` is optional and stays empty unless you want live bill reading. Do not commit a real key. Tests do not need one.

The example file is safe to commit. Real `.env` files are gitignored.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

Other commands:

```bash
npm run lint
npm run build
npm run start
```

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Interactive docs are at http://127.0.0.1:8000/docs while the process is running.

Tests:

```bash
cd backend
source .venv/bin/activate
pytest
```

The dev extra installs `httpx2`, which is what this version of Starlette's `TestClient` imports. The older `httpx` package still runs the client, and Starlette warns that path is deprecated.

`status: "ok"` means the API process handled the request. The payload says Firebase and a complete payable tariff are not connected. The Gemini check stays `not_configured` because health does not call Gemini. Tariff files are inspected and calculated through `/api/tariffs`, not through the health payload.

## Environment configuration

| Variable | Where | Purpose |
| --- | --- | --- |
| `APP_ENV` | Backend | `development`, `test`, or `production` |
| `CORS_ORIGINS` | Backend | Comma-separated explicit `http` or `https` origins. `*` is rejected. The default allows both `localhost:3000` and `127.0.0.1:3000` |
| `NEXT_PUBLIC_API_URL` | Frontend | Base URL of the API |
| `GEMINI_API_KEY` | Backend | Optional Gemini key. Missing key makes bill reading return 503 |
| `GEMINI_MODEL` | Backend | Gemini model. Default `gemini-3.8-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Backend | Extraction timeout. Default 45 |

If `NEXT_PUBLIC_API_URL` is missing, the interface says the API address is not configured. It does not invent a status.

## Current implementation status

Done in this version:

- Blue Hour design tokens, dark and light themes, and the font setup.
- Application shell with a grouped desktop sidebar, a compact header, and a mobile tab bar. `/` redirects to `/dashboard`.
- Overview dashboard built from labeled sample data.
- Bill Auditor at `/bill-auditor`. It uploads a bill, reviews an unconfirmed extraction, and compares confirmed amounts. See [docs/BILL_AUDITOR.md](docs/BILL_AUDITOR.md).
- Meter Readings and Cliff Guard. A person confirms a typed or photographed register. Consumption is calculated by the API. No current tariff file provides a verified threshold, so the gauge is not shown. See [docs/METER_CAPTURE_CLIFF_GUARD.md](docs/METER_CAPTURE_CLIFF_GUARD.md).
- Forecast at `/prediction`. It estimates cycle use from confirmed checkpoints when seven days of history and an explicit cycle start exist. The household budget stays in this browser. A payable rupee total is not calculated. See [docs/PREDICTION_BUDGET_INTELLIGENCE.md](docs/PREDICTION_BUDGET_INTELLIGENCE.md).
- Action Plan at `/action-plan`. Appliance use and what-if schedules are calculated by the API. Records stay in this browser. Rupee savings are not shown. See [docs/APPLIANCE_ACTION_PLAN.md](docs/APPLIANCE_ACTION_PLAN.md).
- History at `/history`. Confirmed checkpoints become measured cycles. A saved forecast can be compared with a finished cycle. Records stay in this browser. Rupee savings are not shown. See [docs/HISTORY_INSIGHTS_SAVINGS.md](docs/HISTORY_INSIGHTS_SAVINGS.md).
- Reusable interface components, including trust and risk indicators.
- FastAPI process health, environment-based CORS, and tests.
- Backend contracts for a household profile, a meter checkpoint, trust labels, decimal amounts, and a public error body. Meter, forecast, appliance, and history routes calculate from records the browser sends. They do not keep those records.
- A versioned tariff engine. IESCO residential energy and fixed-charge rows from the company's February 2026 tariff guide can be calculated. The result is not a payable bill, because taxes and fuel adjustment are not in that source. LESCO, K-Electric, and IESCO protected consumption stay unavailable. See [docs/TARIFF_ENGINE.md](docs/TARIFF_ENGINE.md).

Not done:

- Sign-in, durable meter storage, a payable production bill, a verified Cliff Guard threshold, rupee savings, and notifications. The sample overview does not call the tariff engine. The forecast card on that page does. The sample saving on the overview stays labeled as demo data.

The overview bill, units, chart, checkpoint, and illustrative saving are sample copy. They are marked **Demo data** and carry a trust chip. Cliff Guard shows **Needs verification** and does not state a unit threshold or a protected-consumer status.

## Future feature roadmap

The stage order is written in [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md). The tariff engine is documented in [docs/TARIFF_ENGINE.md](docs/TARIFF_ENGINE.md). Bill reading and audit rules are in [docs/BILL_AUDITOR.md](docs/BILL_AUDITOR.md). Screens still treat overview rupees as sample data.

## Further reading

- [Architecture](docs/ARCHITECTURE.md)
- [Tariff engine](docs/TARIFF_ENGINE.md)
- [Bill auditor](docs/BILL_AUDITOR.md)
- [Meter capture and Cliff Guard](docs/METER_CAPTURE_CLIFF_GUARD.md)
- [Prediction and budget intelligence](docs/PREDICTION_BUDGET_INTELLIGENCE.md)
- [Appliance action plan](docs/APPLIANCE_ACTION_PLAN.md)
- [History, insights, and savings measurement](docs/HISTORY_INSIGHTS_SAVINGS.md)
- [Design system](docs/DESIGN_SYSTEM.md)
- [Development roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [Engineering brief](AGENTS.md)
