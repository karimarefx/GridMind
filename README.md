# GridMind forecasting PoC

Three CPU XGBoost regressors provide rolling **one-hour-ahead** demand, solar and wind predictions. Net load is calculated as demand minus solar minus wind. Start with [the notebook](notebooks/01_xgboost_forecasting.ipynb); reusable training/inference code lives in `src/gridmind/forecasting.py`.

The notebook has been executed locally without cell errors. Seven forecasting checks pass, including future-input leakage and invalid-history handling. The measured pipeline took about 100 seconds. See [held-out results](reports/forecasting/summary.md) and [the first test week](reports/forecasting/test_week.png). Test MAE was 485.98 MW for demand, 359.34 MW for solar, and 645.30 MW for wind; all three improved on last-observation persistence in this held-out period.

## Sample and evaluation

The latest user instruction overrides the earlier full-data recommendation in `plan.md` and `data/README.md`. The experiment uses **17,544 continuous hours**, from `2023-01-01 06:00 UTC` inclusive to `2025-01-01 06:00 UTC` exclusive. It excludes 2021–2022 and the final endpoint. No random hourly sampling, raw-data modification, or observations outside this sample are used for training/context.

The first 168 sampled hours provide common history for weekly baselines. The remaining **17,376 examples** are split chronologically: **13,900 train / 1,738 validation / 1,738 test** (80/10/10, rounded down at boundaries). Splits are assigned by target label before fitting. Each held-out period is about 72 days; this is a compact PoC evaluation, not an ideal universal split or a full-season test. The sample was fixed before inspecting prediction errors. `reports/forecasting/split_manifest.csv` records every assignment.

Increasing the held-out percentages while halving the data does not increase absolute evaluation coverage: these windows are similar in length to the paper's approximately 73-day windows. This choice satisfies the smaller-sample PoC scope; broader seasonal evaluation would need a different protocol.

## Run locally

Use Python 3.11 or 3.12. From this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-forecasting.txt
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m gridmind.forecasting
.\.venv\Scripts\python.exe -m pytest -q
```

Open the notebook in VS Code and select the virtual environment, or use Colab's setup cell. Opening VS Code is optional. The notebook runs the same source functions; it does not maintain a separate feature pipeline. Running training again overwrites the current local bundle/reports; keep the final test frozen during model development.

`requirements-forecasting-lock.txt` records the exact tested local environment. Use it instead of the ranged requirements to reproduce this Windows/Python 3.12 run. The environment prepared in this workspace is at `../.venv`; it can also be selected directly in VS Code.

## Modeling choices

- Demand: 24 historical rows of demand and fixed one-hot local hour/day/month/year calendars.
- Wind: the same calendar and history, plus historical installed wind capacity.
- Solar: 24 historical rows × 15 channels: capacity factor/proxy, 1/2/24/48-hour lags of each, cyclic local hour/day-of-year, daylight flag. Predict the target capacity factor minus its 24-hour lag, then reconstruct MW using **issue-time last-observed capacity**.
- All measured features precede target time. Live inference requires 72 consecutive completed hourly observations. The 168-hour training warmup aligns every comparison with weekly persistence.
- CPU histogram trees, depth 4, learning rate .05, at most 500 trees, seed 42, four threads. Validation early stopping after 30 rounds; test never controls fitting. No hyperparameter search. Uniform solar weights and no scaling.
- Fixed calendar vocabulary (2021–2024 years) avoids fitting encoders; this PoC's year encoding needs review before deployment beyond its source period.
- Demand is nonnegative; renewable predictions use the documented 105% capacity allowance. Solar residuals are clipped in capacity-factor space. Clipping rates are reported.

## Outputs and limitations

`artifacts/forecasting/` contains native model JSON files and the ordered feature/configuration manifest, versioned with this PoC at the user's request. `reports/forecasting/` contains validation/test metrics, predictions, split assignments, run manifest, and a held-out example forecast. Model save/reload and single-request/batch equivalence are checked during training.

Comparisons: last observation, daily persistence, weekly persistence, and solar daily capacity-factor persistence. Metrics include MAE/RMSE in MW, R², MAE skill against persistence, net-load errors, solar daylight errors, seasonal subsets, and peak/ramp subsets with thresholds fitted on training observations. Empty seasonal groups are omitted, not represented as successful coverage.

UTC and hour-ending semantics follow supplied documentation; original workbook provenance/publication timing is not independently verified. The clock-based solar proxy is verified against America/Chicago local hour. Forecast issue assumes each completed hour is immediately available. Last-observed capacity avoids target-capacity leakage but does not prove that retrospective historical capacity was published at issue time. No issued weather, abnormal-input reconstruction, neural reproduction, API/dashboard, or electrical-network integration is included in this forecasting-only change.

XGBoost's validation-based early stopping and native model persistence follow its [official Python API documentation](https://xgboost.readthedocs.io/en/stable/python/python_api.html).
