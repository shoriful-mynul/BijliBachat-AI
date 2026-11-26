# BijliBachat AI 2.0

Don't wait for the bill. Predict it, prevent avoidable overspending, and make better electricity decisions.

BijliBachat AI is a Pakistan-focused household electricity expense product for the Capital Youth Expo Hackathon, Track 3 — FinTech & Financial Inclusion. It is meant to feel like a careful consumer finance app: calm, specific, and honest about what is known.

## Core user journey

Understand → Predict → Prevent → Optimize → Measure

A household should be able to see its electricity position, anticipate the month's expense, stay clear of an avoidable slab change, choose a practical action, and look back at what happened. This repository currently implements the foundation for that journey. The overview uses clearly labeled sample data. Prediction, prevention, and measurement are not calculated yet.

## Technology stack

| Area | Choice |
| --- | --- |
| Frontend | Next.js 16 (App Router), React 19, TypeScript (strict), Tailwind CSS 4 |
| Charts and icons | Recharts 3, Lucide React |
| Backend | Python 3.11+, FastAPI, Pydantic v2, Uvicorn |
| Tests | pytest, FastAPI's `TestClient` |

Planned later, and not connected now: Firebase Authentication, Cloud Firestore, Firebase Storage, and the Google Gemini API (including vision OCR).

## Project structure

```
frontend/          Next.js application
  src/app/         Routes and the root layout
  src/components/  ui, layout, and dashboard components
  src/features/    Overview sample content and settings controls
  src/hooks/       Shared hooks
  src/lib/         Formatting, navigation, theme, health parsing
  src/styles/      Blue Hour tokens
  src/types/       Shared TypeScript types
backend/
  app/api/         HTTP routes
  app/core/        Environment configuration
  app/schemas/     Response models
  app/services/    Health report
  tests/           API tests
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

`frontend/.env.local` only needs the `NEXT_PUBLIC_API_URL` line. `backend/.env` needs `APP_ENV` and `CORS_ORIGINS`. Do not add API keys. None are used in this version.

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

`status: "ok"` means the API process handled the request. The payload also says that Firebase, Gemini, and the tariff file are not connected.

## Environment configuration

| Variable | Where | Purpose |
| --- | --- | --- |
| `APP_ENV` | Backend | `development`, `test`, or `production` |
| `CORS_ORIGINS` | Backend | Comma-separated explicit `http` or `https` origins. `*` is rejected. The default allows both `localhost:3000` and `127.0.0.1:3000` |
| `NEXT_PUBLIC_API_URL` | Frontend | Base URL of the API, for the service-status line only |

If `NEXT_PUBLIC_API_URL` is missing, the interface says the API address is not configured. It does not invent a status.

## Current implementation status

Done in this version:

- Blue Hour design tokens, dark and light themes, and the font setup.
- Application shell with desktop sidebar, header, and a mobile tab bar.
- Overview dashboard built from labeled sample data.
- Reusable interface components, including trust and risk indicators.
- FastAPI process health, environment-based CORS, and tests.

Not done:

- Sign-in, stored households, bill or meter OCR, tariff configuration, bill calculation, Cliff Guard rules, forecasting, budgets, savings calculations, and notifications.

The overview bill, units, chart, checkpoint, and illustrative saving are sample copy. They are marked **Demo data** and carry a trust chip. Cliff Guard shows **Needs verification** and does not state a unit threshold or a protected-consumer status.

## Future feature roadmap

The stage order is written in [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md). Later stages add a verified tariff file and a Python calculation engine before any screen treats a rupee amount as calculated.

## Further reading

- [Architecture](docs/ARCHITECTURE.md)
- [Design system](docs/DESIGN_SYSTEM.md)
- [Development roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [Engineering brief](AGENTS.md)
