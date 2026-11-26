# Development roadmap

The product is built in twelve parts. A later part is not started because a route, a schema, or a sentence exists. Parts 1, 2, and 3 are implemented. Parts 4 through 12 are not.

## 1. Project foundation and design system — done

- Monorepo layout, Next.js frontend, and the FastAPI application factory.
- Blue Hour design system, dark and light themes, and the component set.
- Sample Overview at `/dashboard`, with figures marked as demo data.
- Process health, explicit CORS, and the rule that Python owns tariff and money calculations.

## 2. Frontend application shell and navigation — done

- Shared shell: grouped sidebar, header, and phone navigation.
- `/` redirects to `/dashboard`.
- Cliff Guard, Bill Auditor, Meter Readings, Action Plan, Consumption History, and Settings are reachable. Settings can change the theme on this device. The other screens say the work is not available yet.

## 3. Backend foundation and data architecture — done

- Household, meter checkpoint, trust status, decimal amount, and error contracts.
- Timestamps are timezone-aware and stored as UTC. Amounts use `Decimal`, serialized as strings.
- Unexpected server errors return `ErrorResponse` without the exception text. Field validation stays FastAPI's `detail` list.
- Health and CORS behavior are unchanged. Tests do not need production secrets.
- Firebase, Firestore, Storage, and Gemini have a documented home for later. They are not connected, and no repository returns invented household data.

## 4. Versioned tariff engine — not started

- Dated tariff files, with the distribution company, effective dates, and slabs written as data.
- No universal unit cutoff in code.
- The API refuses a slab question when the file for that company and date is missing.
- The interface keeps showing Unavailable and Needs verification until a file is loaded.
- Protected or non-protected status comes from that file, not from a hardcoded rule.

## 5. Bill auditor and OCR — not started

- Upload a bill and use Gemini for OCR and structured extraction only.
- Uncertain fields stay unconfirmed until a person accepts them.
- Compare a confirmed bill with the Python result for the same cycle.
- Disagreements are labeled "Possible mismatch". The word "fraud" is not used.

## 6. Meter capture and Cliff Guard — not started

- Manual checkpoints and photo checkpoints, stored as checkpoints rather than a live feed.
- A photo extraction stays `pending_confirmation` until a person accepts it.
- Register-order and spike checks belong here, not in the current contract.
- Cliff Guard shows distance to the next verified slab only after the tariff engine exists.

## 7. Prediction and budget intelligence — not started

- An Estimated view of the month if the reading pace continues.
- No invented accuracy percentage.
- A household budget is entered by the household or calculated in Python. It is not estimated silently.

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
- Broader security tests around those connections. The current tests cover contracts, health, and CORS only.

## 12. Deployment and hackathon presentation — not started

- Production configuration, locked CORS origins, and a hosted frontend and API.
- An unverified tariff is still not shown as fact.
- Real notification delivery, if the presentation needs it, is a separate decision. The header bell stays an honest empty state until then.

## Still out of scope

Tariff maths, bill calculation, OCR, meter persistence, Cliff Guard rules, forecasting, budgets, appliance savings, sign-in, and notification delivery.
