# BijliBachat AI

BijliBachat AI helps a Pakistani household understand electricity use, anticipate the month's expense, and choose practical ways to avoid waste.

Tagline: Don't wait for the bill. Predict it, prevent avoidable overspending, and make better electricity decisions.

The journey is Understand, Predict, Prevent, Optimize, Measure.

This file is the permanent engineering brief. The Next.js version in `frontend/` also has its own `AGENTS.md` generated with that install. Read `frontend/node_modules/next/dist/docs/` before changing frontend framework code. The rules below win when they conflict with a generic framework example.

## Authority

Python is the only place electricity tariff calculations and financial calculations may live. The frontend formats numbers it is given. It does not compute bills, slab crossings, savings, or forecasts.

Gemini is limited to OCR, structured extraction, and natural-language explanation. Bill extraction lives in `app/integrations/gemini/`. It must not invent tariff rates, calculate a bill, or change a number that Python produced.

## Tariff truth

Tariff thresholds and protected or non-protected rules come from verified configuration files that carry a date. Do not hardcode a universal 200-unit rule. Do not display an unverified threshold as a fact. If the tariff file is missing, the interface says the data is unavailable and the risk status needs verification.

## Readings and extraction

A manual meter reading and a photo checkpoint are not real-time monitoring. Say that in the interface.

Uncertain OCR fields stay unconfirmed until a person accepts them.

## Numbers people see

Every important number shows its trust status: Verified, Calculated, Extracted, Estimated, or Unavailable. The stored and API values stay those English names. A visible label may be translated. Do not translate a trust value before sending it to the API.

Risk uses color, an icon, and a word together: Safe, Approaching, High risk, or Needs verification.

Demo data is labeled as demo data. Do not invent prediction accuracy, household savings, or social-impact statistics. An illustrative rupee amount in sample copy stays marked as demo and estimated, and the copy says it was not calculated.

When a bill and the household record disagree, the words are "Possible mismatch". Do not write "fraud".

## Secrets and input

Do not put secrets or API keys in frontend code, committed env files, or logs. Validate external data and user input at the boundary that receives it.

Keep the interface accessible and usable at 390px, about 768px, and 1440px. Interactive targets are at least 48px. English and Urdu share the same pages. Urdu is right-to-left. Language is stored only in `bijlibachat.language.v1`. Do not add a translation API or a second copy of a page for Urdu.

## Where work goes

- `frontend/` — Next.js App Router, Blue Hour UI, sample overview.
- `backend/` — FastAPI. Calculation and validation authority. Household and meter contracts live in `app/schemas/`. Tariff maths lives in `app/services/tariff_engine.py` and reads dated files under `app/tariffs/`. Bill comparison lives in `app/services/bill_audit.py` and calls that engine. Routes validate requests and call services. They do not contain tariff formulas or open a database.
- `docs/` — architecture, design system, and the stage plan.

Firebase Authentication, Firestore, and Storage are optional. When Admin credentials or the public client configuration are absent, stay in local/demo mode and do not pretend a write or a sign-in succeeded. Never put a service-account key in frontend code. Do not add rupee savings or notification delivery. A complete payable tariff is still not configured. Meter-photo extraction lives beside bill extraction and must not calculate consumption. The consumption forecast lives in `app/services/prediction.py` and must not invent a payable total. Appliance scenarios live in `app/services/appliances.py` and must not invent wattage or a rupee saving. History comparisons live in `app/services/history.py`, use confirmed checkpoints, and must not turn a kWh difference into a rupee saving or an appliance-caused saving. Do not stub a fake OCR result when Gemini is unavailable. Do not add a tariff rate or a Cliff Guard threshold that is not copied from a verified, dated source.
