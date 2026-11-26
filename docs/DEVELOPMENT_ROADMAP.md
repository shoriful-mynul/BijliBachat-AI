# Development roadmap

Stages are sequential. A later stage is not started by the existence of a route or a placeholder sentence. Only stage 1 is implemented.

## Stage 1 — Foundation (this version)

- Monorepo layout, Next.js frontend, FastAPI backend.
- Blue Hour design system, dark and light themes, and the component set.
- Application shell and the sample Overview at `/dashboard`. `/` redirects there. Other sections are reachable placeholders. A route does not mean that section is built.
- Process health endpoint, explicit CORS, and backend tests.
- Engineering rules for tariff authority, trust labels, and demo data.

## Stage 2 — Verified tariff configuration

- Dated tariff files checked into the backend, with the distribution company, effective dates, and slabs written as data.
- No universal unit cutoff in code.
- The API refuses to answer a slab question when the file for that company and date is missing.
- The interface keeps showing Unavailable and Needs verification until a file is actually loaded.

## Stage 3 — Calculation engine

- Python computes units for a cycle and the rupee amount from the verified file.
- Responses carry Calculated, and the inputs they used.
- The frontend stops using sample rupee amounts once a real result exists, and it still does not recompute them.

## Stage 4 — Household and manual checkpoints

- A household profile and manually submitted meter readings.
- Copy and data model keep checkpoints distinct from live monitoring.
- Validation of dates, register values, and duplicates.

## Stage 5 — Bill and meter capture

- Upload to storage.
- Gemini Vision for OCR and structured extraction only.
- Uncertain fields require a person to confirm them before they are stored as Extracted.

## Stage 6 — Bill auditor

- Compare a confirmed bill with the Python result for the same cycle.
- Disagreements are labeled "Possible mismatch", with the fields that differ.
- No fraud wording, and no automatic accusation.

## Stage 7 — Cliff Guard

- Show distance to the next verified slab only after stage 2 and stage 3 exist.
- Protected or non-protected status comes from the dated file, not from a hardcoded rule.
- The gauge may use a restrained glow only when it represents that verified position.

## Stage 8 — Forecasting

- A clearly Estimated view of the month if the reading pace continues.
- No invented accuracy percentage.
- Any forecast line that uses glow must be a real estimate, labeled as such.

## Stage 9 — Action plan

- Practical actions whose rupee effect, if shown, is calculated in Python from stated assumptions.
- Sample savings copy on the overview is replaced or clearly retired once real calculations exist.

## Stage 10 — History and budget

- Stored cycles, a household budget, and a comparison against that budget.
- Budgets are user-entered or calculated in Python. They are not estimated silently.

## Stage 11 — Accounts and persistence

- Firebase Authentication.
- Cloud Firestore for household data.
- Firebase Storage for bill and meter photos.
- Secrets stay on the server or in the platform's secret store, never in the frontend bundle.

## Stage 12 — Notifications

- Real delivery of reminders the household asked for.
- The header bell stays an honest empty state until then.

## Stage 13 — Deployment

- Production configuration, locked CORS origins, and a hosted frontend and API.
- No change to the rule that an unverified tariff is not shown as fact.

## Out of scope until a stage asks for it

Firebase, Gemini, OCR, tariff maths, protected-consumer classification, forecasting, Cliff Guard business rules, budgets, appliance savings, and notification delivery.
