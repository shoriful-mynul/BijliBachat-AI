# Prediction and budget intelligence

The forecast estimates how much electricity a household may use by the end of the current billing cycle if the pace of its own checkpoints continues. It is not a confirmed bill, and it is not a live meter reading.

`POST /api/predictions/consumption` does the calculation. The browser sends the checkpoints it already keeps from Part 6. The API does not store them.

## Minimum history

A forecast is returned only when all of these are true:

- At least three checkpoints belong to the selected meter.
- The exact time from the earliest to the latest is at least seven complete days. A complete day is 86400 seconds.
- The timestamps are strictly increasing after they are ordered.
- No later register is lower than an earlier one. A decrease is not corrected.
- The cycle start date, cycle end date, and the register at the start of the cycle were sent.
- The latest checkpoint falls inside that cycle.
- The stated moment falls on or after the cycle start, and at least one midnight remains before the cycle end.

Otherwise `forecast_status` is `unavailable`, the projected figures are null, and `missing_inputs` says what is missing. One or two checkpoints do not produce a forecast. A 30-day month is not assumed.

## Formulas

Elapsed days are the exact seconds between two timestamps, divided by 86400.

```text
average_daily_kwh = (latest_register - earliest_register) / elapsed_days
projected_additional_kwh = average_daily_kwh × remaining_days
projected_cycle_kwh = (latest_register - cycle_start_register) + projected_additional_kwh
```

Remaining days are the number of midnights from the stated date until the cycle end date. Cycle consumption uses the register the person supplied for the start of the cycle. An earlier checkpoint is not treated as that start.

Each reported kilowatt-hour figure is quantized to `0.001` with half-up rounding from the exact `Decimal` result. The projection multiplies the exact pace, then quantizes. It does not multiply the already rounded average.

Observed register labels stay as they were stored. Derived past consumption is `Calculated`. Future consumption is `Estimated`. Missing inputs are `Unavailable`. No accuracy percentage is calculated.

The chart plots the real in-cycle checkpoints and, only when a forecast exists, one estimated point on the cycle end date. It does not invent the days in between.

## Budget

`POST /api/predictions/budget` checks a household figure and returns it. It does not save it.

- The monthly budget must be greater than zero, at most `1000000.00` PKR, with two decimal places.
- The optional consumption target must be greater than zero, at most `100000` kWh, with three decimal places.
- Zero, negative, scientific notation, and amounts above those limits are rejected.

The browser stores a valid result under `bijlibachat.budget.v1`. Cycle dates are stored under `bijlibachat.prediction-cycle.v1`. Meter checkpoints stay in `bijlibachat.meter-ledger.v1`. A refresh keeps each of them. Another device does not. Clearing the budget removes only the budget key. A value that is not the expected shape is removed instead of being shown.

The consumption target is compared with the estimated cycle total only. A tariff slab is not used as that target. The comparison is `Estimated`.

## Payable amount

No loaded tariff file contains GST, fuel price adjustment, electricity duty, and a TV fee. Those components are required for a payable total, and they are not treated as zero.

`bill_cost.value` stays null. `comparable_with_budget` stays false. The screen does not say the household is under or over its PKR budget. The consumption forecast can still be shown.

A payable figure would be returned only when the tariff engine resolves a verified, non-synthetic file whose required payable components are all present, and that calculation produces `final_amount`. Partial energy or fixed charges are not copied into this response. Gemini is not asked to price the forecast.

## Tests

```bash
cd backend
pytest
```
