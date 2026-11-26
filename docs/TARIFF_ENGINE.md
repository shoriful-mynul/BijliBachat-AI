# Tariff engine

Python is the only place a tariff amount is calculated. Bill Auditor calls the API, which calls this engine, after a person confirms the bill. Gemini reads a document and must not invent a rate or change a result.

A payable total is returned only when every required component in the matching file is verified and every required input was supplied. No production file meets that bar today, because the verified schedules do not state GST, fuel price adjustment, electricity duty, or a TV fee.

## Configuration files

Production files live in `backend/app/tariffs/configs/`. One JSON file is one scope:

- provider code
- consumer category
- tariff type (`non_tou` or `tou`)
- eligibility, for a non-time-of-use file (`lifeline`, `protected`, or `unprotected`)
- effective date range

`backend/app/tariffs/availability.json` explains companies and categories that have no calculable file. An entry there is not a rate table. A missing rate is never stored as zero.

Each tariff file records:

| Field | Meaning |
| --- | --- |
| `config_id`, `version` | Stable identity of this file |
| `provider_code`, `consumer_category`, `tariff_type`, `eligibility` | Who the file applies to |
| `schedule_name`, `billing_frequency` | Label and billing period. Only `monthly` is accepted |
| `effective_from`, `effective_to` | Inclusive dates. A null end means no published end date, not "use this forever as a fallback" |
| `slab_method` | Required. An unknown method is rejected |
| `verification_status` | `verified`, `unverified`, `needs_verification`, or `incomplete` |
| `synthetic` | Must be false for a file shipped with the API |
| `rounding` | How money components are finished |
| `slabs` | Bands for slab methods. Empty for time of use |
| `fixed_charge`, `minimum_charge` | Each has its own state |
| `time_of_use` | Peak and off-peak rates, only for `time_of_use` |
| `adjustments` | Taxes and other components, each with its own state |
| `source` | Authority, document title, URL, notification date, retrieval date, table reference, verification, and limitations |

Component states:

- `applicable_verified` — the source states the rate or formula, and the engine may use it
- `not_applicable` — the source says the component does not apply
- `unavailable` — the component is required for a payable total, and the rate was not in the source
- `needs_verification` — the source is not clear enough to calculate

A verified adjustment must name a formula. The supported formulas are `percent_of_components` (a percent of the energy, fixed, or minimum charge after those amounts are rounded) and `flat_amount`. Any other state must not carry a rate.

Slab bounds are exclusive at the bottom and inclusive at the top. A null upper bound means the band has no top. Bands in one file cannot overlap. `progressive_marginal` and `one_previous_slab` must start at zero, leave no gaps, and end with an open band.

## Version resolution

The engine selects a file only when the provider code, category, tariff type, eligibility, and billing date all match. Provider codes are compared without case sensitivity. The billing date must fall inside the inclusive effective range.

If nothing matches, the result is unavailable. An older file is not reused. Another company's file is not reused. If two files match, the result is unavailable and neither is used. The loader also refuses to start when two packaged files for the same scope have overlapping dates.

There is no universal unit cutoff in code. There is no protected-consumer classifier. A non-time-of-use request without `eligibility` is refused, including when the consumption would fit a lifeline band. A time-of-use request must not also send an eligibility label.

## Provenance

A production file needs a real `https` URL for the document that was read, the issuing authority, the document title, the notification or publication date when the source states one, the retrieval date, and the table or section that was used. Rates are copied from that document. They are not copied from memory, a news summary, a third-party calculator, or another company's table.

If a schedule cannot be verified, it stays in `availability.json` with the page that was checked and what was missing. It is not given invented numbers.

Synthetic fixtures belong under `backend/tests/`. They are marked `synthetic: true` and use `https://example.com/synthetic-tariff-fixture`. The production loader rejects them.

## Slab methods

The file must name one method.

| Method | Rule |
| --- | --- |
| `single_slab` | The one band that contains total consumption supplies the rate for every unit |
| `progressive_marginal` | Each band supplies the rate for the units that fall inside it |
| `one_previous_slab` | Units up to the previous band's top use that band's rate. Units above it use the current band's rate. Earlier bands are not stacked |
| `time_of_use` | Peak units and off-peak units are priced separately. They must add up to total consumption |

`one_previous_slab` exists so a file can name that rule explicitly. No production file uses it. The IESCO tariff guide says protected consumers receive one previous slab and does not define the arithmetic, so protected residential consumption is not calculated.

The IESCO lifeline rows "Up to 50" and "01-100" are stored as mutually exclusive bands, above 0 through 50 and above 50 through 100, because treating both labels as 1 through 100 would make those rows overlap. That reading is recorded in the lifeline file's limitations.

## Decimal and rounding

Every rate, unit, and amount is a `Decimal`. JSON numbers with a fraction are parsed as `Decimal`. Binary floats and scientific notation are rejected. Money in API responses is a decimal string.

The packaged files use an engine convention because the IESCO guide does not state a rounding rule: each money component is quantized to `0.01` with half-up rounding. Band products stay exact in the slab lines. A percent adjustment uses the already rounded base components, then is itself rounded to a paisa. The payable total, when one exists, is the sum of those rounded components.

A file that asks for a different quantum or rounding mode is rejected.

## Components

The engine can calculate:

- energy charge, by the file's slab method or time-of-use rates
- fixed charge per kW of sanctioned load, using the selected slab's rate
- time-of-use fixed charge: the rate times the higher of half the sanctioned load and MDI
- minimum charge at zero consumption, with separate single-phase and three-phase amounts, only when fixed charges do not apply
- a percent adjustment or a flat adjustment when the file marks that formula verified

A missing sanctioned load, phase, peak units, off-peak units, or MDI is reported in `missing_inputs`. It is not treated as zero. Peak and off-peak units that do not add up to consumption produce no amounts.

The February 2026 note on the IESCO time-of-use row is the one dated exception: through 2026-02-28, a missing MDI uses half the sanctioned load, and the response says so under `assumptions`. After that date, a missing MDI blocks the fixed charge.

## What is verified, and what is not

Retrieved 2026-11-26.

| Scope | Status |
| --- | --- |
| IESCO residential non-time-of-use, confirmed lifeline, from 2026-02-12 | Energy rates and the zero-consumption minimum charge are verified. Fixed charges do not apply. Taxes and fuel adjustment are unavailable, so there is no payable total |
| IESCO residential non-time-of-use, confirmed unprotected, from 2026-02-12 | Energy rates and per-kW fixed charges are verified. Taxes and fuel adjustment are unavailable, so there is no payable total. Zero consumption has no slab, so the fixed charge is not invented |
| IESCO residential time of use, from 2026-02-12 | Peak, off-peak, and the Rs 675 per kW fixed-charge rule are verified. Taxes and fuel adjustment are unavailable, so there is no payable total |
| IESCO residential protected | Not calculated. The one-previous-slab formula is not defined on the source page |
| IESCO protected residential, prepaid residential, and other published categories | Not configured. Protected rows are on the same table, without a defined slab-benefit formula. The prepaid residential row and the other category tables were read and were not loaded |
| LESCO | Not configured. [The LESCO tariff page](https://www.lesco.gov.pk/3000063) still shows a schedule headed W.E.F 05-11-2021 and conflicting historical tables |
| K-Electric | Not configured. [The K-Electric FAQ](https://ke.com.pk/faqs/) dates S.R.O. 279(I)/2026 as 12 February 2026 and describes fixed charges. A variable-charge table was not available as readable text, so IESCO's variable rates were not copied |

The IESCO rates were read from [the IESCO tariff guide](https://iesco.com.pk/tariff-guide), which cites S.R.O. No. 279(I)/2026, February 2026. The gazette PDF was not retrieved in this pass. The day 12 February 2026 comes from K-Electric's statement of that same SRO. No effective end date was published on the IESCO page.

These files do not include a later periodic adjustment. A billing date before 2026-02-12 does not use them.

## Unavailable results

The calculation response uses the existing trust labels. The overall label is `Calculated` only when `outcome` is `calculated` and `final_amount` is present. Otherwise the overall label is `Unavailable`, even if an energy or fixed-charge line inside `components` is `Calculated`.

`final_amount` is null when the provider is unsupported, the category is unknown, no file covers the date, two files match, the file is not verified, an input is missing, the consumption is outside the confirmed category's bands, or a required component has no verified rate. The response includes `reason_code`, `reason`, `missing_inputs`, and `blocking_components`. It does not invent a number for those gaps.

`GET /api/health` stays `not_configured` for tariff configuration. Packaged energy and fixed-charge files are not a complete payable tariff. The tariff routes are where those files are listed.

## API

List metadata, including source and limitations:

```bash
curl http://127.0.0.1:8000/api/tariffs
```

Resolve one scope. This does not calculate money:

```bash
curl "http://127.0.0.1:8000/api/tariffs/resolve?provider_code=IESCO&consumer_category=residential&tariff_type=non_tou&eligibility=unprotected&billing_date=2026-03-01"
```

Calculate. Send decimal strings. A fractional JSON number is rejected because it becomes a binary float.

```bash
curl -X POST http://127.0.0.1:8000/api/tariffs/calculations \
  -H "Content-Type: application/json" \
  -d '{
    "provider_code": "IESCO",
    "consumer_category": "residential",
    "tariff_type": "non_tou",
    "eligibility": "unprotected",
    "billing_date": "2026-03-01",
    "consumption_kwh": "250",
    "sanctioned_load_kw": "5"
  }'
```

That request can return an energy charge and a fixed charge. `final_amount` is null until GST, fuel price adjustment, electricity duty, and TV fee are present in a verified file. An unsupported company, a missing input, or a date outside the file returns the same response shape with no invented total.

Invalid bodies and invalid query dates return FastAPI's `422` field-error list. `GET /api/health` is unchanged in shape.

## Adding a provider or a new version

1. Read the official notification or the distribution company's own schedule. Record the URL, the date it was retrieved, and the table used.
2. Add a new JSON file under `backend/app/tariffs/configs/`. Do not edit an old file into a new effective period. Give the new file its own `config_id` and `effective_from`. Set `effective_to` on the previous file when the source replaces it.
3. Set `slab_method` to the method the source actually describes. Do not assume progressive bands or a single band.
4. Mark each tax and adjustment with its own state. Leave unknown rates out of the file rather than as zero.
5. Keep `synthetic` false and `verification_status` aligned with the source block.
6. If the document is not sufficient, add an `availability.json` entry instead of a rate file.
7. Add a test that locks the copied rates and a test that a date outside the new window does not select the file.
8. Run `pytest` from `backend/`. The application loads these files at startup and refuses overlapping scopes.

Household and meter records are still not stored, and this engine is not wired to the frontend.
