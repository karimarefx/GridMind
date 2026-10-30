# Forecasting dataset

The team supplied [`raw/ercot_2021_2024_hourly.csv`](raw/ercot_2021_2024_hourly.csv) for GridMind's demand, solar, and wind forecasting POC. The CSV is copied unchanged and explicitly versioned at the user's request. Do not modify this source file during preprocessing.

## Use the full dataset

Use all valid hourly records across the four-year release for the forecasting experiment, rather than a random 10% sample. The file is approximately 4 MB and contains only 35,065 rows. This is manageable for CPU XGBoost in Colab and preserves seasons, peaks, renewable ramps, and capacity changes.

Using the full dataset does **not** mean fitting on every row. The preferred chronological allocation remains approximately 2021–2022 training, 2023 validation, and 2024 test, as described in [the POC plan](../plan.md). Assign exact boundaries by target interval after resolving the documented source hour-ending convention and endpoint. Fit learned preprocessing only on the training partition.

Use 4–8 consecutive weeks only for an initial smoke test. Reduce to the plan's smaller contiguous subsets only if measured preprocessing or training costs require it. Usable supervised examples will be fewer than raw rows because of historical feature requirements: 24 hours for demand/wind, 72 hours for solar, and 168 hours for weekly-baseline comparisons.

## Initial inspection — 31 October 2026

| Check | Result |
|---|---|
| File size | 4,023,732 bytes |
| Data rows | 35,065 |
| Columns | 8 |
| First timestamp as stored | `2021-01-01 06:00:00` |
| Last timestamp as stored | `2025-01-01 06:00:00` |
| Consecutive timestamp steps | All 35,064 are exactly one hour |
| Duplicate timestamps | 0 |
| Empty cells | 0 |
| Non-finite numeric values | 0 |
| Negative numeric values | 0 |
| Nonpositive solar/wind capacities | 0 |
| Solar/wind generation above 105% of capacity | 0 |
| Maximum absolute net-load arithmetic difference | 0 MW at parsed floating-point precision |

Columns, in source order:

```text
time,wind_generation,wind_installed,total_load,solar_generation,solar_installed,net_load,clear_sky_proxy
```

SHA-256 of the unchanged file:

```text
de3486a1795551ccbee47f09d69545d974dde38ea7a763601fefe2b42ee642f7
```

## Remaining checks before training

- Timestamps contain no explicit timezone offset. The existing forecasting specification identifies them as UTC with source hour-ending semantics; confirm this provenance before assigning final splits.
- The release extends into 1 January 2025. Do not create an unintended fourth partition from endpoint labels or silently discard them before resolving interval meaning.
- Validate the supplied proxy against its documented local-hour formula and confirm feature construction.
- Verify source version, attribution, usage conditions, and original-workbook reconciliation where available. Receipt and numerical consistency alone do not verify these.
- Establish capacity availability at forecast issue time. Retrospective installed-capacity values must not leak into forecasts.
- Solar generation has small positive values even near zero; define daylight masks from the documented proxy/calendar policy rather than treating every positive value as daylight.

This inspection did not clean, preprocess, train, or evaluate a model. Full model-readiness checks remain required.
