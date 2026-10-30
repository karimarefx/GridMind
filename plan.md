# GridMind 10% Proof of Concept

**Proposal discussion:** 10 November 2026

**Planning date:** 31 October 2026

**Status:** Proposed work; no implementation or training started.

## 1. Scope, authority, and acceptance criteria

Build a local dashboard demonstrating GridMind’s five capabilities. Train only:

1. **Forecasting:** three XGBoost regressors predicting demand, solar generation, and wind generation one hour ahead.
2. **Event diagnosis, stage 1:** one XGBoost classifier distinguishing sensor/measurement problems from physical grid abnormalities.

Demonstrate missing-telemetry reconstruction, cascading-risk prediction, and corrective-action recommendation through deterministic, interactive frontend simulations.

### Authoritative specifications and POC overrides

Use the existing documents in `Model_Documentation`, particularly:

- [Demand and renewable forecasting](Model_Documentation/GridMind_Demand_Renewable_Forecasting.md)
- [Event diagnosis](Model_Documentation/EVENT_DIAGNOSIS.md)
- [Whole-system overview](Model_Documentation/GridMind_Whole_System_Overview.md)

The remaining model specifications define the concepts represented by the frontend simulations.

| Existing specification | POC decision |
|---|---|
| Forecasting leads with LSTM, compares FCNN, and treats XGBoost as optional | User instruction overrides architecture and comparisons: train XGBoost only; retain the documented task, source data, features, solar transformation, units, and constraints |
| Forecasting reference uses approximately 90/5/5 chronological splits | Use the seasonal evaluation split below; identify results as an adapted POC, not an unchanged reproduction |
| Diagnosis compares Random Forest and XGBoost | Train XGBoost; use a simple non-trained baseline |
| Diagnosis includes LSTM physical-event localization | Exclude stage 2; location output is unavailable |
| Diagnosis dataset is unresolved; PSML is only a candidate | Inspect supplied files before committing to training; compatible sensor examples remain a data-readiness requirement |
| Full-system documents describe trained reconstruction/risk/action models and electrical validation | Defer these; display interactive illustrations without claims of learned inference or physical validation |

### Acceptance criteria

- Dashboard runs locally without Colab connectivity after setup.
- All four trained estimators load from exported artifacts and produce reproducible local inference.
- Supplied data passes documented inspection before feature generation or training.
- Held-out results include baselines, split definitions, sample counts, limitations, and measured runtime.
- Every actual learned output displays **“Model prediction.”**
- Every reconstruction, cascade, and recommendation illustration displays **“Simulated demonstration.”**
- Observations and calculations have separate provenance labels.
- A rehearsed demonstration completes in approximately seven minutes.
- Invalid inputs, missing artifacts, insufficient history, and unsupported events produce explicit unavailable/error states.
- Beating baselines is a research goal, not a condition for honestly demonstrating a working pipeline. Failure to improve must be reported.

Exclude live SCADA, equipment control, event localization, normal-operation detection, neural models, weather integration, new power-flow infrastructure, and claims of grid safety.

## 2. Stack, repository, and computing budget

### Recommended stack

- **Training/evaluation:** Google Colab notebooks, Python, pandas, NumPy, scikit-learn, XGBoost.
- **Local inference:** FastAPI, Pydantic, Uvicorn, shared Python feature-generation functions.
- **Frontend:** React, TypeScript, Vite, Recharts; SVG for the illustrative network.
- **Storage:** CSV/Parquet datasets, JSON manifests and scenario fixtures; no database required.
- **Tests:** pytest and a small browser smoke-test suite.

Use CPU histogram-based XGBoost initially; no GPU dependency. Pin the exact working dependency versions after the first Colab/local compatibility smoke test.

### Repository structure

```text
GridMind/
  plan.md
  Model_Documentation/
  notebooks/                 # inspection, forecasting, diagnosis
  data/
    raw/                     # team-supplied; immutable and gitignored
    manifests/               # checksums, schemas, split/group assignments
    processed/               # reproducible, gitignored
    demo/                    # small permitted replay inputs
  src/gridmind/
    inspection/
    features/
    training/
    inference/
  backend/
  frontend/
  scenarios/                 # versioned illustrative fixtures
  artifacts/
    forecasting/
    diagnosis/
  reports/                   # inspection, metrics, limitations
  tests/
  requirements-colab.txt
  requirements-local.txt
  README.md
```

Keep large data and model binaries outside ordinary Git history; document the local artifact installation procedure.

### Resource limits and experiment budget

- Local target: **8 GB system RAM, four CPU threads, no GPU**.
- Run one API worker, load models once, and retain only needed replay windows in memory.
- Engineering target: backend working memory below 2 GB and combined demonstration processes below 4 GB; measure on the actual laptop.
- Local inference target: warm p95 below one second per request, measured over 100 representative requests.
- Colab: record available CPU, RAM, package versions, and actual peak memory. Resources are not guaranteed; persist exports after each completed run. See the [Colab resource FAQ](https://research.google.com/colaboratory/faq.html).
- Start with one configuration per estimator. Permit at most two additional configurations per estimator.
- Budget approximately two hours per component for feature generation and initial experiments. A run projected to exceed 30 minutes triggers simplification before expanding the search.
- These are stop rules and performance targets, not measured promises.

## 3. Dashboard and demonstration workflow

### Pages

| Page | Charts and information | Controls |
|---|---|---|
| Overview | Five capability cards, illustrative network, source/provenance legend, current scenario | Scenario selector, reset |
| Forecasting | Demand/solar/wind history, next-hour forecasts, actuals when revealed, calculated net load, baseline comparison | Replay issue time, series selection, reveal next observation |
| Event diagnosis | Electrical traces, observation-window boundaries, predicted category, raw model score, quality warnings | Held-out episode selector, sensor/physical examples, insufficient-input example |
| Scenario laboratory | Missing/reconstructed traces, illustrative propagation animation, candidate-action comparison | Missingness mask, hypothetical outage, stress level, action choice, animation step |
| Evaluation and provenance | Metrics, confusion matrix, split periods, independent-event counts, manifests, versions, limitations | Model/report selection |

Forecast charts use MW and explicit issue/target timestamps. Electrical event channels retain their actual units. The network is an illustrative 14-bus layout, not a claim that ERCOT or the event dataset was measured on that network.

### Workflow

1. Select a dataset-backed forecasting replay hour.
2. Generate the three real forecasts locally.
3. Reveal the subsequent observed hour and compare against baselines.
4. Select an independently held-out event episode and run real stage-1 diagnosis.
5. Open the scenario laboratory and explicitly choose a separate illustrative scenario.
6. Mask telemetry, animate an assumed cascade, and compare scripted interventions.
7. Reset to a known starting state.

A diagnosis must not automatically identify a failed component: stage 1 supplies no location. Any outage selected for cascade illustration is a user-selected hypothetical contingency.

## 4. Dataset inspection and readiness gate

The team downloads and supplies files. Do not download replacement datasets or assume that the documented release matches the delivered files.

### Inspect before preprocessing

1. Inventory filenames, sizes, hashes, source/version, attribution, and usage conditions.
2. Read headers and small samples before loading large archives.
3. Record schema, row counts, timestamp conventions, units, missingness, duplicates, numerical ranges, and identifiers.
4. Validate cadence, ordering, gaps, sequence boundaries, and timezone/DST handling.
5. Check labels and label meanings against the source documentation.
6. Identify duplicate/near-duplicate event episodes, shared parent runs, and related variants.
7. Record exclusions and unresolved ambiguities; retain raw files unchanged.
8. Produce a readiness report and frozen sampling/split manifest.

**Forecasting gate:** coherent hourly demand, solar, wind, and capacities with trustworthy timestamps. Verify prepared CSV features against the documented formulas.

**Diagnosis gate:** defensible physical and sensor labels, compatible channels/cadence, and enough identifiable independent parent episodes.

If event-family identifiers cannot be recovered, do not claim an independently held-out evaluation from random row splits.

Missing units, irreconcilable timestamps, unidentified labels, or incompatible datasets block the affected training pipeline.

## 5. Forecasting sampling plan

### Recommended amount

The specification reports **35,065 hourly rows for ERCOT 2021–2024**, including an endpoint. Verify that count and interval interpretation on receipt.

| Level | Recommended size | Reason |
|---|---|---|
| Preferred and recommended | Full supplied 2021–2024 release, approximately 35,065 hourly rows | Small enough for CPU tree models; multiple annual cycles and a full-year test support credible seasonal evaluation |
| Minimum useful POC | 24 consecutive complete months, approximately 17,520–17,544 hourly rows | Supports more than one year of training under 70/15/15, but shorter held-out periods limit seasonal conclusions |
| Reduced fallback | 12 consecutive complete months, approximately 8,760–8,784 hourly rows | Demonstrates the pipeline; training and test cannot both cover an annual cycle, so annual robustness is unproven |
| Smoke test only | 4–8 continuous weeks | Checks implementation and runtime; insufficient for proposal-level forecasting claims |

“10% implementation” does not mean using 10% of the rows.

### Selection and splits

- Preferred: **2021–2022 training, 2023 validation, 2024 test**, approximately **50/25/25**.
- Assign by forecast target interval/year after resolving the hour-ending convention and extra endpoint.
- Minimum/fallback: chronological **70/15/15**, with exact date boundaries frozen before fitting.
- Select continuous complete periods; do not randomly sample hours.
- Prefer the full release. If reduced coverage is necessary, select the longest valid contiguous period using inspection quality and coverage, without examining model test errors.
- Preserve nights, weekdays/weekends, seasons, demand peaks, renewable ramps, and capacity changes.
- Do not delete unusual operating periods merely because they are difficult to predict.

### Cadence, horizon, and history

- Preserve hourly resolution and a **one-hour forecast horizon**.
- Demand and wind use the documented 24-hour input windows.
- Solar uses the documented 24-row window containing lags up to 48 hours: **72 raw hours of history** are required.
- Require 168 hours for the weekly baseline; align baseline/model comparisons on common eligible target timestamps.
- Training-example counts are smaller than raw-row counts; publish actual counts after feature validity checks.
- Unexpected subhourly data requires explicit interval-aware aggregation; unexpected coarse data does not support the existing hourly task without a specification change.

### Leakage controls

- Assign target-time partitions before generating windows.
- Fit encoders and other learned transforms only on training data.
- A later partition may use earlier observations as historical context when those values would have been available at issue time.
- Historical test observations may enter later rolling forecasts after becoming available; no test-driven retraining.
- Overlapping historical inputs across chronological boundaries are acceptable for this rolling one-hour task. Randomly splitting overlapping windows is not.
- Exclude target/future generation, retrospective capacity updates, and future-derived rolling statistics.
- Freeze the test period; do not tune against it.

**Provisional until inspection:** actual cadence, usable years, exact counts, issue-time data availability, capacity publication timing, and whether source workbooks reproduce the prepared CSV.

## 6. Event-diagnosis sampling plan

### Independent events determine sample size

Use one feature record per complete supplied abnormal observation sequence for the primary experiment. This avoids manufacturing apparent sample size from highly overlapping windows.

| Level | Independent parent families | Class coverage target | Reason |
|---|---:|---|---|
| Preferred and recommended | About 1,000 | At least 500 independent event episodes represented per class | Approximately 100 independent examples per class in a 20% test partition gives useful preliminary evidence |
| Minimum useful POC | About 200 | At least 100 independent episodes represented per class | Approximately 20 test episodes per class; results will have wide uncertainty |
| Reduced fallback | About 100 | At least 50 independent episodes represented per class | About 10 test episodes per class; feasibility evidence only |

Counts are targets, not claims that the files contain these examples. When multiple episodes share a parent family, they do not increase the independent-family count.

Raw measurement volume is:

**sum of sequence durations × sampling frequency × channel count**

Report raw rows, complete sequences, and independent parent families separately. A million rows from a few disturbances is not a large independent evaluation set.

### Representative selection

- Inventory physical subtypes, operating conditions, locations, severities, noise levels, and available sensor-problem types.
- Select complete episodes across these conditions without breaking their time order.
- Keep rare supported conditions where feasible; publish per-stratum counts and unsupported classes.
- Do not mix incompatible grids, channel definitions, units, or sampling rates simply to balance classes.
- Prefer a common compatible subset of channels and one source domain for this milestone.
- Exclude mixed sensor-plus-physical cases from binary training unless their labeling policy is defensible; retain examples for an explicitly unsupported-case demonstration.

### Splitting and grouping

- Target **60% training / 20% validation / 20% test**, stratified by broad class at the **parent-family level**.
- Keep all related operating-point variants, fault variants, duplicate exports, corruption variants, and windows in one partition.
- If a continuous recording supplies multiple episodes, group the recording and apply non-overlap checks.
- When chronological deployment evaluation is feasible, preserve chronology while maintaining family separation; record deviations from the target proportions.
- If group constraints prevent adequate test coverage, report the achieved allocation and reduce the strength of claims.
- Do not oversample validation or test data. Use training-only weighting for imbalance.

### Controlled sensor examples

If real sensor labels are absent, use the approved semi-synthetic route:

- Start from clean normal-operation episodes compatible with the physical-event data.
- Split parent families **before** generating corruptions.
- Generate bounded bias, drift, stuck readings, and intermittent spikes, documenting affected channels, duration, severity, and seed.
- Preserve temporal structure and related uncorrupted channels.
- Avoid using file format, length, missing-value tokens, or corruption metadata as accidental class identifiers.
- Keep corruption variants attached to their parent group.
- Evaluate across severity ranges; reserve a separate corruption-type challenge where sample counts permit.
- Report conclusions as **physical events versus controlled sensor corruptions**, not validated detection of arbitrary real sensor failures.

If compatible clean episodes or defensible labels are unavailable, block binary training and show the limitation. Do not substitute dashboard simulation results for real classifier evaluation.

**Provisional until inspection:** source dataset, independent-family counts, class balance, compatible channels, sequence durations, cadence, corruption ranges, and supported operating conditions.

## 7. Preprocessing, training, and evaluation

### Forecasting

- Preserve documented UTC/hour-ending semantics and derive local calendar features using `America/Chicago`.
- Validate one-to-one joins, hourly continuity, duplicates, missing values, and numerical ranges.
- Do not silently interpolate gaps or remove extremes. Skip invalid windows with an exclusion report.
- Flatten the documented time-window features in a fixed order for XGBoost:
  - Demand: historical demand and documented calendar encoding.
  - Wind: generation, installed capacity, and documented calendar encoding.
  - Solar: documented 15-channel capacity-factor/proxy/lag/calendar representation.
- Retain the solar residual target: target-hour capacity factor minus capacity factor 24 hours earlier.
- Reconstruct solar MW using capacity available at issue time. Use last-known capacity if future publication timing is unavailable, and document this limitation.
- Retain the documented nonnegative/capacity postprocessing; report clipping frequency.
- Scaling is unnecessary for tree fitting; any retained transformation must be fitted only on training data and exported.
- The solar weighting formula is not fully specified in the Markdown: use uniform weights for the POC unless an authoritative supplied implementation resolves it; document the deviation.

**Baselines:** last observation, 24-hour persistence, 168-hour persistence, and capacity-factor daily persistence for solar.

**Metrics:** per-target MAE/RMSE in MW, R², baseline skill, calculated net-load error, seasonal/peak/ramp breakdowns, and solar daylight versus all-hour errors. Define peak/ramp thresholds from training data. Avoid solar MAPE near zero and “percentage accuracy” claims.

### Diagnosis

- Retain original observations; do not feed frontend reconstruction simulations into the classifier.
- Validate channel order, units, cadence, sequence completeness, and component mapping.
- Extract fixed per-channel summaries: mean, standard deviation, minimum, maximum, range, mean absolute first difference, and maximum absolute first difference.
- Add aligned-channel co-change summaries only where channel semantics support them.
- Exclude labels, filenames, scenario IDs, fault codes, known event locations, and post-event metadata from features.
- Use complete supplied abnormal windows; describe diagnosis as window-level retrospective classification, not real-time onset detection.
- Reject incompatible or incomplete sequences for this POC instead of introducing an unvalidated imputation pipeline.

**Baseline:** training-set majority-class classifier.

**Metrics:** macro-F1, balanced accuracy, per-class precision/recall, physical-event miss rate, confusion matrix, and independent-family counts. Include family-level bootstrap intervals where viable; otherwise report counts and acknowledge uncertainty.

XGBoost probabilities are raw scores unless calibration is evaluated. Use validation data to choose a binary threshold maximizing macro-F1, breaking ties in favor of physical-event recall. Return `uncertain` for unsupported or invalid inputs; do not invent a confidence-based abstention threshold.

### Bounded training protocol

Start with seed 42, CPU `hist`, at most four threads:

- Initial configuration: depth 4, learning rate 0.05, up to 500 trees, subsample 0.8, column sample 0.8.
- Validation early stopping: 30 non-improving rounds.
- Regression: squared-error objective; classification: binary logistic objective.
- If justified by validation, test depths 3 and 6; no broad search.
- Use training-only inverse-frequency class weights for diagnosis.
- Freeze the selected configurations before final test evaluation.

If preprocessing or fitting exceeds budget, reduce search/tree counts first, then apply the predefined fallback subset. Report fallback results separately; do not select a subset based on favorable test scores.

## 8. Colab export, inference API, and integration

### Required export bundle

After each completed Colab run, export:

- Executed notebook and reusable feature/training source.
- Three forecasting models and one diagnosis model.
- Native XGBoost JSON/UBJSON models.
- Fitted encoders and any preprocessing artifacts.
- Ordered feature definitions, units, lag/window rules, target transformations, class mapping, and threshold.
- Source hashes, split/group assignments, exclusions, corruption recipes/seeds.
- Metrics, baseline outputs, representative inference fixtures, and model-card limitations.
- Exact dependency versions, Python version, parameters, best iteration, and training hardware.

Native model export does not replace the preprocessing and training manifest. See [XGBoost model persistence documentation](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html).

Download and verify exports before ending the Colab session.

### Local interfaces

- `GET /health`: artifact availability and versions.
- `GET /demo/catalog`: permitted replay hours, event episodes, and scenario identifiers.
- `POST /forecast`: validated hourly history, region, issue time, and available capacities.
- `POST /diagnose`: abnormal observation sequence, timestamps, channels, units, and component mapping.
- `GET /evaluation`: frozen metrics and data/split summaries.

Forecast response: issue time, target time, one-hour horizon, demand/solar/wind MW, calculated net-load MW, quality status, and model version.

Diagnosis response: sensor/physical/uncertain, raw score where valid, observation window, diagnosis time, limitations, and model version. Return physical location as unavailable because stage 2 is excluded.

Common metadata: request/scenario identifier, dataset/source identifier, timestamps, units, provenance, and artifact version.

Return explicit schema-validation errors for malformed inputs and unavailable status for absent artifacts or unsupported data. Never silently return fixtures as live model predictions.

Run feature generation from shared Python code in both Colab and the local API.

## 9. Frontend simulations and provenance

Use small versioned JSON fixtures and deterministic frontend rules. No trained models or new electrical simulator are required.

- **Reconstruction:** hide readings from an illustrative in-service component; reveal an illustrative interpolated trace with a separate missingness mask. Preserve original/reference values. Equipment status remains separate.
- **Cascade:** select a hypothetical outage and animate scripted propagation rounds. Use qualitative illustrative severity, not calibrated failure probabilities.
- **Corrective actions:** compare no-change, redispatch, and renewable-curtailment illustrations. Include scripted before/after values and an unsuccessful example.
- State **“Illustrative outcome; physics validation not implemented”** on action comparisons.
- Changes to controls update the appropriate fixture/rule outcome; unsupported combinations return unavailable.
- Reset restores the scenario and clears stale results.

### Output classification

| Output | Classification | Required display |
|---|---|---|
| Supplied ERCOT history | Observed dataset value | “Observed — ERCOT dataset” |
| Supplied event trace | Dataset input; origin may itself be simulation | “Dataset input” plus source origin |
| Controlled sensor-corruption trace | Synthetic input | “Synthetic sensor corruption” |
| Demand/solar/wind forecasts | Predicted | **“Model prediction”** |
| Diagnosis produced by XGBoost, including on synthetic inputs | Predicted | **“Model prediction”** plus input provenance |
| Net load from forecast components | Calculated from predictions | “Calculated from model predictions” |
| Errors, metrics, baseline values | Calculated | “Calculated” plus formula/baseline |
| Reconstruction illustration | Simulated | **“Simulated demonstration”** |
| Cascade sequence/severity/DNS illustration | Simulated | **“Simulated demonstration”** |
| Candidate actions and before/after illustration | Simulated | **“Simulated demonstration”** |
| Unsupported location, missing prediction | Unavailable | “Unavailable” with reason |

Provenance must appear on cards, charts, tooltips, and exported screenshots—not only in a global disclaimer.

## 10. Prioritized checklist and five-member ownership

| Priority | Deliverable | Responsible | Dependency / reviewer |
|---|---|---|---|
| P0 | Obtain datasets, attribution, and source descriptions | Member 1 — integration lead | Team supplies files |
| P0 | Inspect data; freeze schemas and split/group manifests | Member 2 — forecasting; Karim — diagnosis | Member 5 reviews leakage |
| P0 | Shared feature definitions and API contracts | Member 1 + model owners | Inspection gates |
| P0 | Forecast baselines and three XGBoost regressors in Colab | Member 2 | Forecast readiness |
| P0 | Event grouping, sensor examples, baseline, XGBoost | Karim — Member 3 | Diagnosis readiness |
| P0 | Dashboard shell and two real-model pages | Member 4 — frontend | Contracts; fixtures allowed during development |
| P0 | Export bundles, local API, and parity checks | Member 1 | Model exports |
| P0 | Independent evaluation and acceptance evidence | Member 5 — QA/evaluation | Frozen models and test sets |
| P1 | Three interactive simulations and provenance labels | Member 4 | Scenario definitions reviewed by model owners |
| P1 | Integrated rehearsal and offline package | Member 5 + Member 1 | P0 integration |
| P2 | Visual polish and additional supported scenarios | Member 4 | All acceptance checks passed |

Every member reviews one other member’s output. Member 5 audits split independence; Member 1 owns integration decisions and tracks unresolved blockers.

## 11. Schedule backward from 10 November

All dates use Cairo local time.

| Date | Required outcome |
|---|---|
| **10 Nov** | Proposal discussion; demonstrate frozen release; no training or environment changes |
| **9 Nov** | Two full rehearsals on the presentation laptop; verify offline backup, fonts, ports, and reset workflow |
| **8 Nov** | Feature freeze; acceptance checks, final metrics, screenshots, and fallback recording |
| **7 Nov** | Integrate real API/model outputs with dashboard; verify Colab/local parity and resource targets |
| **6 Nov** | Export selected models and preprocessing; complete untouched test evaluation and limitations |
| **5 Nov** | Finish bounded validation experiments; freeze model settings and thresholds |
| **4 Nov** | Initial Colab training and baselines; simulations interactive |
| **3 Nov** | Shared feature pipelines, API contracts, inspection fixes, and smoke runs complete |
| **2 Nov** | Data-readiness gates; freeze subsets/splits; activate fallback plans for unresolved files |
| **1 Nov** | Team supplies files; inspect schemas, sequences, labels, timestamps, and parent identifiers |
| **31 Oct** | Agree ownership and scope; prepare environment and data-delivery checklist |

Dataset delivery after 2 November threatens credible two-component evaluation. Keep dashboard work moving using visibly marked development fixtures; never present those fixtures as trained evidence.

## 12. Committee script, essential tests, risks, and fallbacks

### Seven-minute demonstration

1. **0:00–0:40:** Explain the limited scope: two trained components, three interactive illustrations.
2. **0:40–2:10:** Replay ERCOT history, request next-hour forecasts, reveal actuals, compare baselines.
3. **2:10–3:30:** Diagnose one held-out physical episode and one sensor example. Explain semi-synthetic labels where applicable and stage-2 exclusion.
4. **3:30–5:20:** Mask telemetry, choose a hypothetical outage, animate propagation, and compare scripted actions. Point to **“Simulated demonstration.”**
5. **5:20–6:30:** Show independent-event counts, forecast split years, metrics, limitations, and local runtime.
6. **6:30–7:00:** Demonstrate insufficient-input handling and explain next research steps.

### Essential tests

- Forecast target is exactly one hour after issue time.
- Solar features require the full 72-hour history; weekly baseline requires 168 hours.
- DST/hour-ending handling, duplicates, gaps, invalid capacities, and target alignment.
- Feature generation never reads future observations or retrospectively unavailable capacity.
- No parent event family or derived corruption crosses partitions.
- Export/reload and Colab/local feature parity; predictions agree within documented numerical tolerance.
- Correct solar reconstruction, clipping, net-load arithmetic, class mapping, and threshold use.
- API rejects invalid units, channel order, missing history, and incompatible sampling.
- UI shows correct provenance and clears stale predictions after input changes.
- Deterministic scenario reset; hypothetical outage is not inferred from stage-1 diagnosis.
- Both real inference flows work offline within the local resource target.

### Risks and fallback actions

| Risk | Response |
|---|---|
| Forecast training is slow | Reduce tree/search budget first; use the predefined continuous fallback only if needed |
| Too few independent events | Report the smaller effective sample and wider uncertainty; do not inflate counts with windows |
| Sensor class absent | Use approved compatible clean-episode corruptions and label evaluation semi-synthetic |
| No compatible sensor source or trustworthy labels | Mark diagnosis training blocked; present dataset gap honestly |
| Missing capacity publication history | Use documented last-known capacity and limit claims |
| Models fail to beat baselines | Show actual results and error breakdowns; investigate without changing the test set |
| Colab disconnects | Persist each completed bundle and resume from manifests; avoid one long notebook dependency chain |
| Local memory pressure | One worker, sequential model requests, limited replay cache, no training dependencies |
| API or laptop failure during discussion | Show timestamped saved real inference results as **“Recorded model prediction”**, plus an offline recording; identify replay explicitly |
| Scenario illustrations appear physically validated | Keep simulation badges and validation-unavailable text visible |
| Schedule slips | Cut optional charts/scenarios and tuning before cutting inspection, provenance, or held-out evaluation |

Remaining data-dependent decisions must be resolved in the 1–2 November inspection report. No performance result, sample availability, or successful training is assumed by this plan.
