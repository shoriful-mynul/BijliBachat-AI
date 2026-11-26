# Meter capture and Cliff Guard

Meter readings are checkpoints a person submits, usually every few days. They are not a live feed from the meter. Cliff Guard calculates what it can from those checkpoints and says when a tariff threshold is not available.

## Storage

The API does not keep checkpoints. `create_app()` installs `NotRetainedLedger`, which records nothing.

| Event | What happens to a confirmed checkpoint |
| --- | --- |
| Browser refresh | It remains, because this browser stored it in `localStorage`. |
| New visit in the same browser | It remains. |
| API restart | Nothing is restored. The API never stored it. |
| Another device | It is not there. |

The browser key is `bijlibachat.meter-ledger.v1`. Photos are not written there. A future repository can replace `NotRetainedLedger` without changing the validation or Cliff Guard formulas. `ProcessLocalLedger` exists only so tests can exercise that boundary. The running API does not use it.

## Endpoints

- `POST /api/meter-readings/extractions` reads a JPEG, PNG, or WebP up to 8 MB. The response is an unconfirmed draft.
- `POST /api/meter-readings` validates one confirmed checkpoint against `prior_readings` sent with it. The register is not rewritten.
- `GET /api/meter-readings` returns an empty list and the storage limitation, unless a test ledger was installed.
- `GET /api/cliff-guard` calculates an empty ledger and reports what is missing.
- `POST /api/cliff-guard` calculates the checkpoints the caller sends.

`MeterReading` stays a domain contract and is not an HTTP schema. Routes use separate request and response models.

## Meter photo

Gemini uses the same server key, model, and `google-genai` client as bill extraction, with a separate meter schema. It may return the visible register, the unit label, and the meter number, plus confidence. It does not calculate consumption.

An unreadable digit stays blank. It is not stored as zero. `confirmed` is always false. A low-confidence reading sets `requires_manual_review`. Nothing is saved until `POST /api/meter-readings` receives `confirmation: "user_confirmed"` and the value the person submitted. If they change the extracted number, the saved trust label is `Verified`. If they accept the photo value unchanged, the trust label stays `Extracted`.

## Validation

The server checks the submitted register. It does not trust a consumption figure from the browser.

- The register is a non-negative decimal with at most three decimal places.
- The time must include a timezone.
- A repeated time, or the same register on the same day for the same meter, is rejected.
- A time earlier than the latest checkpoint for that meter is rejected. It is not inserted into the history.
- A different meter number is a separate series.
- A lower register is not accepted until the person sends `review_decision: "keep_as_submitted"`. The explanation names replacement, rollover, correction, or a typing error, and does not choose one.
- A possible reading anomaly is a review flag, not a tariff rule. It applies when both the previous interval and the new interval last at least one day, and the new daily pace is more than three times the previous pace. The register is not changed. The phrase is `Possible reading anomaly`.

## Calculations

All of these use `Decimal`.

- Consumption between two checkpoints is the later register minus the earlier register. A decrease is not turned into a consumption figure.
- Average daily use is that consumption divided by the elapsed days. Elapsed days are the exact seconds between the timestamps divided by 86400. Zero elapsed time does not produce an average.
- Billing-cycle consumption is the latest register minus `cycle_start_register_kwh`, and only when that start register and both cycle dates were sent and the latest checkpoint falls inside the cycle. An older checkpoint is not treated as the cycle start.
- A safe daily allowance is remaining units divided by remaining days. Remaining days are the midnights until the cycle end date. The function returns nothing when the remaining units are negative or the remaining days are not positive, so it does not recommend a negative allowance.
- A projection needs at least three checkpoints spanning two days, a verified threshold, and remaining units. The pace is the change from the earliest checkpoint to the latest, divided by the days between them. The result is `Estimated`. Otherwise the message is `Not enough reading history for a reliable projection.` or `Threshold needs verification for this tariff configuration.`

## Threshold

No loaded tariff file contains a verified Cliff Guard threshold. Slab edges are rate bands. They are not used as the threshold, and crossing one is not treated as a change of eligibility.

When a company, tariff type, and billing date are supplied, the API resolves the existing tariff file. If a file matches, `threshold_status` is `needs_verification`, `threshold_kwh` is null, and the response names that file. The gauge is not drawn unless `threshold_status` is `verified` and a threshold value is present. That state does not occur for the current files.

Adding a threshold later means a dated, sourced field on a tariff file. It should not be a hardcoded number in Cliff Guard.

## Privacy

The Gemini key stays on the server. Photos are read from memory and the buffer is cleared after success and failure. Logs do not include the photo. Tests use a fake extractor and do not call Gemini.

## Tests

```bash
cd backend
pytest
```
