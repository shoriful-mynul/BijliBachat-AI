# Bill auditor

The Bill Auditor reads an electricity bill image or PDF, asks a person to confirm the fields, and compares those confirmed fields with the Python tariff engine. The reading is not a confirmed bill, and a partial tariff result is not a payable total.

## Gemini

The server uses the official `google-genai` SDK, version 1.75.0 (`google-genai>=1.75,<2`). The client is `google.genai.Client`. Documents are sent inline to `client.interactions.create` with `store=False`. Images use input type `image`. PDFs use input type `document`. The response is constrained with a JSON schema. Money and quantities are strings in that schema so they are not parsed as binary floats.

The model name is `GEMINI_MODEL`. The default is `gemini-3.8-flash`. It is not repeated in the extraction or audit code.

Official references used for this implementation:

- SDK: https://googleapis.github.io/python-genai/
- Image input: https://ai.google.dev/gemini-api/docs/image-understanding
- PDF input: https://ai.google.dev/gemini-api/docs/document-processing
- Structured output: https://ai.google.dev/gemini-api/docs/structured-output
- Model status: https://ai.google.dev/gemini-api/docs/deprecations

Gemini may read visible text and return a field, a confidence label (`readable`, `uncertain`, `unreadable`, or `missing`), and a short note. It must not calculate a bill, choose a slab, decide protected status, invent a tax, or judge the document. The prompt says a missing charge is null, not zero.

If `GEMINI_API_KEY` is missing, the extraction route returns HTTP 503 and `code: "unavailable"`. A timeout, an invalid JSON body, a schema violation, or an upstream failure does the same. The API does not substitute a sample extraction.

The key stays in backend settings. It is not a `NEXT_PUBLIC_` variable, it is not written into the health payload, and request logs record the exception type only.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | unset | Server key. Leave it empty in the example file. |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Model passed to the Interactions API. |
| `GEMINI_TIMEOUT_SECONDS` | `45` | Client timeout. The SDK also receives the same duration in milliseconds. |

Automated tests construct a fake extractor or patch `google.genai.Client`. `pytest` does not need a key and does not call Gemini.

## Uploads

Accepted files are JPEG, PNG, WebP, and PDF. The limit is 8 MB (`8 * 1024 * 1024` bytes), which is under the inline request sizes described for images and PDFs.

The route reads the body into a buffer and checks the signature:

- JPEG starts with `FF D8 FF` and ends with `FF D9`.
- PNG starts with the PNG signature and contains `IHDR`.
- WebP is a `RIFF` container with `WEBP`.
- PDF starts with `%PDF-` and contains `%%EOF`.

The filename is ignored. A declared content type must match the signature when the browser sends one. Empty, oversized, truncated, and unknown files are rejected with HTTP 400. The buffer is wiped after success and after failure. No upload directory is created, and the document is not written to Firestore or to the API response.

## Extraction

`POST /api/bills/extractions` returns a draft with `confirmed: false`. Each field has a value, a confidence label, `readable`, a note, and trust status `Extracted` or `Unavailable`.

Fields: provider code, consumer category, tariff type, eligibility, billing date, due date, meter number, billed units, peak and off-peak units, current and previous readings, sanctioned load, energy charges, fixed charges, fuel price adjustment, GST, electricity duty, TV fee, arrears, other printed charges, and total amount due.

A provider is mapped only from an explicit company code or a known company name (`IESCO`, `LESCO`, `K-Electric`, `HESCO`). A date must already be `YYYY-MM-DD`. A tariff type or eligibility is kept only when the printed text is an explicit label. Anything else stays blank.

## Confirmation and audit

`POST /api/bills/audits` accepts `confirmation: "user_confirmed"` plus the values from the form. A boolean, a confidence label, or the extraction draft is not accepted. The route calls `calculate_tariff`. It does not contain a tariff formula.

Comparison outcomes are `match`, `possible_mismatch`, `not_comparable`, and `unavailable`. They are not trust labels.

A possible mismatch requires both amounts, the same component, a verified calculation, and a difference greater than 1.00 PKR. That 1.00 PKR band is an audit tolerance, not a tariff rule. It is included in the report limitations.

A blank bill component is not compared as zero. A tariff component with no amount is `unavailable`, not a mismatch. Arrears and other printed charges are `not_comparable`.

The current IESCO files calculate energy and fixed charges only. GST, fuel price adjustment, electricity duty, and TV fee are unavailable, so `complete_payable_comparison` is false. The bill total is not compared with the energy-and-fixed subtotal. The report says a complete payable comparison is unavailable.

`POST /api/bills/complaint-drafts` runs the same audit again and fills a template. The draft is editable, uses confirmed values, says "Possible mismatch" only when a comparison has that outcome, and is not submitted.

## Interface

`/bill-auditor` uploads a file, shows the unconfirmed fields, and enables the audit after the person checks that they reviewed the form. Editing the form clears that check. The audit view shows each comparison, the tariff file when one was resolved, and the unavailable payable comparison. The complaint box can be edited and copied. It states that nothing was submitted.

## Tests

```bash
cd backend
pytest
```

No Gemini key is required. The frontend checks are `npm run lint`, `npx tsc --noEmit`, and `npm run build` in `frontend/`.
