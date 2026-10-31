# Sampled XGBoost baseline results

Sampled rows: 17,544; common eligible target hours: 17,376.

| Split | Examples | First target (UTC) | Last target (UTC) |
|---|---:|---|---|
| train | 13,900 | 2023-01-08 06:00:00+00:00 | 2024-08-09 09:00:00+00:00 |
| validation | 1,738 | 2024-08-09 10:00:00+00:00 | 2024-10-20 19:00:00+00:00 |
| test | 1,738 | 2024-10-20 20:00:00+00:00 | 2025-01-01 05:00:00+00:00 |

## Final test (all hours)

| Target | Model MAE (MW) | Persistence MAE (MW) | Daily MAE (MW) | Weekly MAE (MW) | Model RMSE (MW) | MAE skill vs persistence |
|---|---:|---:|---:|---:|---:|---:|
| demand | 485.98 | 1106.50 | 2091.49 | 3554.60 | 642.10 | 56.1% |
| solar | 359.34 | 1234.13 | 1274.41 | 1905.27 | 720.61 | 70.9% |
| wind | 645.30 | 884.66 | 6877.69 | 8541.42 | 880.42 | 27.1% |
| net_load | 837.76 | 1868.06 | 6475.22 | 8620.61 | 1119.57 | 55.2% |

Positive skill means lower MAE than persistence. These are measured held-out errors, not percentage accuracy.

## Validation and reproducibility

Validation alone controls early stopping. The single fixed configuration was frozen before test evaluation. Native model reload predictions matched exactly; the exported one-hour interface matched the first test prediction. Complete per-model results, daylight/season/peak/ramp subsets and baseline scores are in metrics.csv.

Measured pipeline runtime: 76.48 seconds (excludes environment setup).

## Limitations

- UTC hour-ending semantics follow supplied documentation, not an independent workbook audit.
- Assumes completed source hour is available immediately at issue time.
- Last-observed installed capacity used for clipping/reconstruction; historical publication timing unverified.
- Uniform solar weights; no weather; no neural-model reproduction.
- Held-out windows do not cover all seasons; no full-year generalization claim.
