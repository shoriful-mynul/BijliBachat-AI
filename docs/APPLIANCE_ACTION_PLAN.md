# Appliance action plan

A household can enter the appliances it uses, see the calculated consumption, and compare that schedule with a different one. The difference is a scenario. It is not a measured saving, and it is not a rupee amount.

The API does not keep the records. This browser keeps them.

## Contract

An appliance has an id, a name the household chooses, an optional category, rated watts, quantity, hours on a day it runs, optional days each week, and optional notes. Two appliances can share a name. Wattage is not treated as verified, because the household entered it.

`input_source` is `entered_by_household`. Calculated use is `Calculated`. A scenario difference is `Estimated`. A missing figure is `Unavailable`.

## Endpoints

- `POST /api/appliances/consumption` accepts the appliances and an optional day count.
- `POST /api/appliances/scenarios` accepts the saved schedule, the proposed schedule, and the day count. The two lists must contain the same appliance ids.
- `POST /api/appliances/action-plan` uses that same scenario body. An action is created only for an appliance whose proposal differs.

Invalid watts, quantity, hours, or days return a validation error. They are not replaced with zero.

## Formulas

On a day the appliance runs:

```text
daily_kwh = (rated_watts × quantity × operating_hours_per_day) / 1000
```

When days per week are omitted, those hours apply on every day of the period:

```text
period_kwh = daily_kwh × days
```

When days per week are entered:

```text
period_kwh = daily_kwh × days × operating_days_per_week / 7
```

For a scenario:

```text
saved_kwh = baseline_period_kwh − scenario_period_kwh
percentage = (saved_kwh / baseline_period_kwh) × 100
```

The percentage is calculated only when the baseline is greater than zero. A negative result is described as more electricity, not as a saving. The absolute difference is shown separately.

The arithmetic uses `Decimal`. Displayed kWh are quantized half-up to `0.001` after the exact result. Percentages are quantized half-up to `0.01`. Intermediate values are not rounded. The day count must be from 1 to 366. A 30-day month is not assumed. Watts must be greater than zero and at most 100000. Quantity must be from 1 to 100. Hours must be greater than zero and at most 24.

## Storage

`bijlibachat.appliances.v1` holds the saved appliances. `bijlibachat.appliance-scenario.v1` holds the day count and the proposed hours, quantity, and weekly days. A refresh keeps both. Another device does not. Deleting an appliance removes its proposal. A stored value that is not the expected shape is dropped. Photos and Gemini are not involved.

## Rupee savings

No loaded tariff file contains GST, fuel price adjustment, electricity duty, and a TV fee. Those components are not treated as zero, and no per-unit price is assumed. `pkr_impact.value` stays null. The screen says so in the main content, not only in a footnote.

## Tests

```bash
cd backend
pytest
```
