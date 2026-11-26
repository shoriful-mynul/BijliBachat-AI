# Development roadmap

The product is built in twelve parts. A later part is not started because a route, a schema, or a sentence exists. Parts 1 through 7 are implemented. Parts 8 through 12 are not. No distribution company has a complete payable tariff or a verified Cliff Guard threshold.

## 1. Project foundation and design system — done

- Monorepo layout, Next.js frontend, and the FastAPI application factory.
- Blue Hour design system, dark and light themes, and the component set.
- Sample Overview at `/dashboard`, with figures marked as demo data.
- Process health, explicit CORS, and the rule that Python owns tariff and money calculations.

## 2. Frontend application shell and navigation — done

- Shared shell: grouped sidebar, header, and phone navigation.
- `/` redirects to `/dashboard`.
- Cliff Guard, Bill Auditor, Meter Readings, Action Plan, Consumption History, and Settings are reachable. Settings can change the theme on this device. Bill Auditor, Cliff Guard, and Meter Readings were placeholders in this part. Bill Auditor is implemented in Part 5. Cliff Guard and Meter Readings are implemented in Part 6. The other screens say the work is not available yet.

## 3. Backend foundation and data architecture — done

- Household, meter checkpoint, trust status, decimal amount, and error contracts.
- Timestamps are timezone-aware and stored as UTC. Amounts use `Decimal`, serialized as strings.
- Unexpected server errors return `ErrorResponse` without the exception text. Field validation stays FastAPI's `detail` list.
- Health and CORS behavior are unchanged. Tests do not need production secrets.
- Firebase, Firestore, Storage, and Gemini have a documented home for later. They are not connected, and no repository returns invented household data.

## 4. Versioned tariff engine — done

- Dated JSON schedules and a Decimal engine. The method is declared on each file: one slab for all units, progressive bands, one previous slab, or time of use. There is no universal unit cutoff in code.
- IESCO residential lifeline, unprotected, and time-of-use energy and fixed-charge rows were copied from the company's tariff guide for S.R.O. 279(I)/2026. GST, fuel price adjustment, electricity duty, and TV fee are not in that guide, so those calculations have no payable total.
- Protected residential consumption is not calculated. The guide does not define the one-previous-slab arithmetic, and the engine does not classify a household from the current month's units.
- LESCO and K-Electric have no loaded rates. The pages that were checked, and what was missing, are recorded in `availability.json`.
- The API can list files, resolve one scope, and calculate. A missing file, a missing input, or an unverified component returns an unavailable result and does not substitute another rate.
- The sample overview is not connected to this engine. Bill Auditor calls it after a person confirms a bill. The format and the source notes are in [TARIFF_ENGINE.md](TARIFF_ENGINE.md).

## 5. Bill auditor and OCR — done

- `POST /api/bills/extractions` accepts a JPEG, PNG, WebP, or PDF up to 8 MB, checks the file signature, and asks Gemini for a structured reading. The draft is `confirmed: false`. A missing key or a bad model response returns 503 and does not invent fields.
- The review screen keeps every extracted field editable. The audit accepts `confirmation: "user_confirmed"` and the submitted values. Confidence does not confirm a field.
- The audit calls the existing tariff engine and compares equivalent components. A difference above 1.00 PKR is a possible mismatch. The bill total is not compared with an energy-and-fixed subtotal.
- A complaint draft is a local template. It is not submitted.
- Bills are not stored. The details are in [BILL_AUDITOR.md](BILL_AUDITOR.md).

## 6. Meter capture and Cliff Guard — done

- A person can type a register reading or review one taken from a meter photo. The photo draft stays unconfirmed, and an unreadable digit stays blank.
- Confirmed checkpoints are validated for order, duplicates, a lower register, and a possible reading anomaly. The API does not keep them. This browser does, and a photo is not stored.
- Consumption, average daily use, and an explicit billing cycle are calculated in Python. A safe daily allowance and a crossing date are calculated only when their inputs exist.
- No loaded tariff file contains a verified Cliff Guard threshold. Slab edges are not used as one, so the gauge stays hidden and the page says the threshold needs verification. See [METER_CAPTURE_CLIFF_GUARD.md](METER_CAPTURE_CLIFF_GUARD.md).

## 7. Prediction and budget intelligence — done

- `POST /api/predictions/consumption` estimates cycle use from at least three checkpoints spanning seven complete days. The pace is exact `Decimal` arithmetic. A shorter history stays unavailable.
- The household can enter a monthly PKR budget and an optional kWh target. Both stay in this browser, separate from meter checkpoints. The kWh target is not a tariff slab.
- A payable rupee forecast is unavailable. The loaded files do not contain GST, fuel price adjustment, electricity duty, or a TV fee, and those gaps are not treated as zero. The PKR budget is not compared with a partial tariff. See [PREDICTION_BUDGET_INTELLIGENCE.md](PREDICTION_BUDGET_INTELLIGENCE.md).

## 8. Appliance action plan and what-if simulator — not started

- Practical actions whose rupee effect, when shown, is calculated in Python from stated assumptions.
- Sample savings copy on the overview is replaced or clearly retired once a real calculation exists.

## 9. History, insights, and savings measurement — not started

- Stored cycles and a comparison of actual use with an estimate.
- Savings figures come from Python. The interface does not invent them.

## 10. Localization and accessibility — not started

- Urdu and English copy, including the Noto Nastaliq face already loaded for later Urdu text.
- The shell's current contrast, focus, and 48px targets stay in place while language support is added.

## 11. Integration, security, and testing — not started

- Firebase Authentication.
- Cloud Firestore for household data, behind the repository boundary.
- Firebase Storage for bill and meter photos.
- Secrets stay on the server or in the platform secret store, never in the frontend bundle.
- Broader security tests around those connections. Current tests cover contracts, health, tariffs, and bill extraction with a fake Gemini client.

## 12. Deployment and hackathon presentation — not started

- Production configuration, locked CORS origins, and a hosted frontend and API.
- An unverified tariff is still not shown as fact.
- Real notification delivery, if the presentation needs it, is a separate decision. The header bell stays an honest empty state until then.

## Still out of scope

Appliance savings, sign-in, notification delivery, and durable meter storage. Meter photos and bill images are read temporarily and are not stored. A payable production bill and a verified Cliff Guard threshold are also still out of scope until a verified file contains them.
