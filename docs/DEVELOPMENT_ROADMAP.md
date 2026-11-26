# Development roadmap

The product is built in twelve parts. A later part is not started because a route, a schema, or a sentence exists. Parts 1 through 10 are implemented. Parts 11 and 12 are not. No distribution company has a complete payable tariff or a verified Cliff Guard threshold.

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

## 8. Appliance action plan and what-if simulator — done

- A household can enter appliances and compare a proposed schedule. Daily and period use are exact `Decimal` calculations. The difference is a scenario, not a measured saving.
- Actions are created only from a change the household entered. No wattage or rupee saving is invented.
- PKR savings stay unavailable because the loaded tariffs omit GST, fuel price adjustment, electricity duty, and the TV fee. The overview sample saving remains labeled demo data and links to the action plan. See [APPLIANCE_ACTION_PLAN.md](APPLIANCE_ACTION_PLAN.md).

## 9. History, insights, and savings measurement — done

- Confirmed checkpoints can be grouped into a cycle. Actual use is the register difference. Two cycles from the same meter can be compared, with a warning when their lengths differ.
- A forecast snapshot is copied only when the existing forecast is estimated. The comparison with measured use does not change that forecast and is not an accuracy score.
- A kWh target is a figure the household entered for one cycle. PKR savings stay unavailable. See [HISTORY_INSIGHTS_SAVINGS.md](HISTORY_INSIGHTS_SAVINGS.md).

## 10. Localization and accessibility — done

- English remains the default. Urdu switches the whole interface to a right-to-left layout and Noto Nastaliq Urdu. The choice is `bijlibachat.language.v1` in this browser and does not replace the theme.
- Navigation, page copy, forms, empty states, trust labels, and chart tables use one typed dictionary. API sentences stay in English and are isolated in Urdu layout. Meter, forecast, appliance, and history formulas are unchanged. PKR savings stay unavailable.
- Labels, keyboard dialogs, focus, and chart text alternatives were checked with the existing pages. This is not a certified WCAG audit. See [LOCALIZATION_ACCESSIBILITY.md](LOCALIZATION_ACCESSIBILITY.md).

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

Sign-in, notification delivery, durable meter storage, and rupee savings from a partial tariff. Meter photos and bill images are read temporarily and are not stored. A payable production bill and a verified Cliff Guard threshold are also still out of scope until a verified file contains them.
