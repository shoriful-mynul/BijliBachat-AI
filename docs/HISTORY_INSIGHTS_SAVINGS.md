# History, insights, and savings measurement

A household can group confirmed meter checkpoints into a billing cycle, compare two cycles, and compare a finished cycle with a forecast it saved earlier. The figures are measurements or previous estimates. A lower number is not a rupee saving, and it does not prove that an appliance action caused the change.

The API does not keep the records. This browser does.

## Data

A cycle is two confirmed checkpoints from the same meter. The browser copies the registers accepted at that moment. Deleting the cycle does not delete the checkpoints. If a checkpoint later disappears from the meter list, the cycle still shows the registers it saved and says the link is gone.

A forecast snapshot is stored only when `POST /api/predictions/consumption` would return `estimated`. Saving it calls that same forecast and copies the projected kWh. It does not change the forecast. An unavailable forecast produces no snapshot.

A kWh target is optional and refers to one cycle id. It is a figure the household entered. It is not a verified baseline.

## Endpoints

- `POST /api/history/cycles/validate` accepts two confirmed checkpoints and the cycles already saved in the browser.
- `POST /api/history/cycles/compare` compares an earlier cycle with a later one from the same meter.
- `POST /api/history/forecast-snapshots` copies a valid forecast.
- `POST /api/history/forecast-comparisons` subtracts that saved forecast from measured cycle use.
- `POST /api/history/baseline-comparisons` compares measured use with the entered target for the same cycle.
- `POST /api/history/insights` states a trend only when two valid cycles exist for the same meter.

Invalid numbers, an unconfirmed checkpoint, and a malformed value are rejected. They are not replaced with zero.

## Rules and formulas

Actual use:

```text
actual_cycle_kwh = ending_register_kwh − starting_register_kwh
```

Duration is the exact elapsed time between the timestamps, divided by 86400 seconds. It is not a count of calendar dates. Average daily use is actual use divided by that duration.

```text
usage_difference_kwh = earlier_cycle_kwh − later_cycle_kwh
forecast_difference_kwh = actual_cycle_kwh − forecast_cycle_kwh
```

A positive forecast difference means actual use was higher. A negative difference means it was lower. A percentage is calculated only when the forecast, or the earlier cycle when the lengths are comparable, is greater than zero. A zero forecast has no percentage.

Cycles whose durations differ by more than one day still show both totals, with a warning. The comparison to read is average daily use.

The arithmetic uses `Decimal`. Displayed kWh are quantized half-up to `0.001` after the exact result. Percentages are quantized half-up to `0.01`. Intermediate values are not rounded.

A cycle is rejected when the checkpoints differ in meter, the end is not later, the register falls, the id or checkpoint pair already exists, or the period overlaps another cycle for that meter. Cycles that only touch at an endpoint are allowed.

## Trust and wording

Measured use and the differences are `Calculated`. The saved forecast is `Estimated`. A missing comparison is `Unavailable`. The target is described as entered by the household. It is not labeled `Verified`.

The interface may say measured use was lower or higher than a previous cycle, a saved forecast, or an entered target. It does not say an appliance saved energy, that efficiency improved, or that a rupee amount was saved.

## Storage

`bijlibachat.meter-ledger.v1` remains the confirmed checkpoints. History adds:

- `bijlibachat.history-cycles.v1`
- `bijlibachat.forecast-snapshots.v1`
- `bijlibachat.history-baselines.v1`

A refresh keeps them. Another device does not. A stored value that is not the expected shape, including a bad date, a bad number, or a duplicate id, is dropped. The API remains stateless: it calculates from what the browser sends and does not hold an independent copy.

## Rupee savings

No loaded tariff file contains GST, fuel price adjustment, electricity duty, and a TV fee. Those components are not treated as zero, and no per-unit price is assumed. `pkr_impact.value` stays null.

## Tests

```bash
cd backend
pytest
```
