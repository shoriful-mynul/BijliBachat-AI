# BijliBachat AI

BijliBachat AI helps a Pakistani household understand electricity use, anticipate the month's expense, and choose practical ways to avoid waste.

Tagline: Don't wait for the bill. Predict it, prevent avoidable overspending, and make better electricity decisions.

The journey is Understand, Predict, Prevent, Optimize, Measure.

This file is the permanent engineering brief. The Next.js version in `frontend/` also has its own `AGENTS.md` generated with that install. Read `frontend/node_modules/next/dist/docs/` before changing frontend framework code. The rules below win when they conflict with a generic framework example.

## Authority

Python is the only place electricity tariff calculations and financial calculations may live. The frontend formats numbers it is given. It does not compute bills, slab crossings, savings, or forecasts.

Gemini, when it is added, is limited to OCR, structured extraction, and natural-language explanation. It must not invent tariff rates, calculate a bill, or change a number that Python produced.

## Tariff truth

Tariff thresholds and protected or non-protected rules come from verified configuration files that carry a date. Do not hardcode a universal 200-unit rule. Do not display an unverified threshold as a fact. If the tariff file is missing, the interface says the data is unavailable and the risk status needs verification.

## Readings and extraction

A manual meter reading and a photo checkpoint are not real-time monitoring. Say that in the interface.

Uncertain OCR fields stay unconfirmed until a person accepts them.

## Numbers people see

Every important number shows its trust status: Verified, Calculated, Extracted, Estimated, or Unavailable.

Risk uses color, an icon, and a word together: Safe, Approaching, High risk, or Needs verification.

Demo data is labeled as demo data. Do not invent prediction accuracy, household savings, or social-impact statistics. An illustrative rupee amount in sample copy stays marked as demo and estimated, and the copy says it was not calculated.

When a bill and the household record disagree, the words are "Possible mismatch". Do not write "fraud".

## Secrets and input

Do not put secrets or API keys in frontend code, committed env files, or logs. Validate external data and user input at the boundary that receives it.

Keep the interface accessible and usable at 390px, about 768px, and 1440px. Interactive targets are at least 48px.

## Where work goes

- `frontend/` — Next.js App Router, Blue Hour UI, sample overview.
- `backend/` — FastAPI. Future calculation and validation authority.
- `docs/` — architecture, design system, and the stage plan.

Do not add Firebase, Firestore, Gemini, bill OCR, meter OCR, tariff maths, forecasting, Cliff Guard rules, budgets, or notification delivery until that stage is explicitly requested. Prepare a clean boundary for them instead of stubbing a fake result.
