# GridMind: Demand and Renewable Forecasting

**Decision reference and implementation plan**  
**Updated:** 30 October 2026  
**Scope:** One of GridMind's five AI functions.

This document records the forecasting decisions agreed in the project discussion. It separates the planned GridMind implementation from findings about research papers and from optional extensions. It is not a claim that training, deployment or integration has already been completed.

## 1. Purpose and agreed description

> Demand and Renewable Forecasting predicts electricity demand, solar generation and wind generation one hour ahead. It supplies separate power forecasts to downstream grid analysis and corrective-action planning. It does not itself predict line overloads or component-risk scores.

GridMind is a software-only, human-in-the-loop decision-support prototype for transmission-grid control-center engineers. A demonstration monitors one simulated network containing buses, lines, transformers, generators and loads. Other benchmark networks may be evaluated separately.

The project does not connect to the Egyptian national grid, require confidential SCADA measurements, or automatically operate real equipment. Public time series drive simulated scenarios; they are not represented as measurements from the benchmark network.

## 2. Confirmed decisions

| Item | Agreed initial scope |
|---|---|
| Forecast targets | Electricity demand, solar generation and wind generation |
| Horizon | One hourly step ahead |
| Data resolution | Hourly |
| Update pattern | Rolling updates as new hourly history becomes available |
| Output units | MW, with explicit issue and target timestamps |
| Geographic level | Aggregate source/control-area forecasts |
| Learning task | Supervised regression, not classification |
| Primary reference | ERCOT indirect neural forecasting study |
| Initial dataset | Released ERCOT 2021–2024 series |
| Leading candidate | Indirect LSTM |
| Internal arrangement | Three separately trained predictors behind one forecasting interface |
| Required comparisons | Persistence, daily/weekly seasonal persistence, indirect FCNN and indirect LSTM |
| Optional comparator | Gradient-boosted trees, such as XGBoost |
| Weather | Optional separately evaluated extension |
| Electrical topology | Not an input of the initial forecasting networks |
| Net load | Calculated from the three forecasts, not a replacement for them |
| Component-risk analysis | Separate downstream integration and network analysis |

The research foundation and first-version scope are selected. The final trained configuration is not predetermined: validation and held-out evaluation must establish which candidate is suitable.

## 3. What the module does

The module takes validated historical data, prepares the same features used during training, runs the three predictors, converts their results to MW, aligns their target timestamps and returns one forecast record.

```text
Historical electricity data + capacities + calendar/proxy features
                              |
                  Validate and prepare inputs
                              |
          +-------------------+-------------------+
          |                   |                   |
     Demand LSTM         Solar LSTM           Wind LSTM
          |                   |                   |
     Demand MW            Solar MW             Wind MW
          +-------------------+-------------------+
                              |
             Net load = demand - solar - wind
                              |
          Timestamped forecast service output
                              |
          Separate downstream network analysis
```

There is no additional “big LSTM” surrounding these predictors. The outer module is ordinary preparation and orchestration code. Each predictor has its own learned weights. This remains one functional module within GridMind.

The diagram shows the leading LSTM candidate. The FCNN comparison uses the same functional arrangement with separately trained FCNN predictors.

### Example

At an illustrative issue time of 10:00, the module supplies a next-hour forecast:

| Output | Illustrative value |
|---|---:|
| Demand | 1,000 MW |
| Solar generation | 200 MW |
| Wind generation | 100 MW |
| Derived net load | 700 MW |

These are explanatory numbers, not experimental results. Net load is remaining demand after subtracting solar and wind. It is not a line flow, overload probability or complete dispatch plan.

## 4. Why one hour ahead

The initial GridMind demonstration emphasizes monitoring, anticipating near-term stress and testing possible corrective actions. A rolling next-hour forecast supports that purpose while keeping implementation manageable for the team.

At each update, the service uses only information available at its issue time. An earlier test observation may be used once it has become historical; this is normal rolling forecasting, not a long forecast made at the start of the test period.

The ERCOT labels follow an hour-ending convention. Preserve the source timestamp and interval meaning. Do not describe hourly labels as instantaneous measurements or claim 15-minute performance from interpolated hourly data. A live deployment would also need to account for reporting delays.

Day-ahead forecasting serves a different purpose: preparing tomorrow's dispatch, storage and flexibility plans. It remains a possible later extension, not an additional required first-version deliverable. Forecast horizon, point-versus-probabilistic outputs, and joint-versus-separate learning are independent design choices.

## 5. Primary research reference and selection rationale

**Paper:** *Net Load Forecasting with Renewable Capacity Features: A Comparison of Direct and Indirect Neural Network Methods*, Oluwafolajimi Samuel Bolusteve, Linhan Fang and Xingpeng Li, arXiv:2604.17012v2.

- [Paper](https://arxiv.org/abs/2604.17012v2)
- [Repository](https://github.com/rpglab/ML_ERCOT-NetLoad_Forecasting)
- Previously audited repository revision: `a0c8d526a2d39280b5604bd8fa3bc23198367f1e`.

ERCOT is the source electricity system, not the model's name. The study compares direct FCNN, indirect FCNN, direct LSTM and indirect LSTM. Direct models predict net load alone. Indirect methods predict demand, solar and wind separately, then subtract renewable generation from demand.

The indirect approach fits GridMind because separate consumption and generation values are needed downstream. Identical net load can arise from different demand/generation combinations, with different electrical consequences once allocated to network locations.

The reference was selected for its target match, one-hour experiment, manageable public data, available implementation and comparison methods. Selection is not a claim that LSTM is universally best or that Texas performance transfers automatically to other systems.

## 6. Dataset and availability

The inspected release includes four ERCOT source workbooks for 2021–2024, a prepared CSV, preparation/training notebooks and saved predictions. These were accessible without university sign-in in the earlier review.

The prepared CSV has **35,065 hourly rows and eight columns**. UTC timestamps cover 1 January 2021 at 06:00 through 1 January 2025 at 06:00, including both endpoints. This is the total raw row count, not the training-example count.

| Column | Meaning |
|---|---|
| `time` | UTC timestamp; retain the source hour-ending meaning |
| `total_load` | Aggregate demand, MW |
| `solar_generation` | Reported solar production, MW |
| `solar_installed` | Installed solar capacity, MW |
| `wind_generation` | Reported wind production, MW |
| `wind_installed` | Installed wind capacity, MW |
| `net_load` | Demand minus solar minus wind, MW |
| `clear_sky_proxy` | Dimensionless clock-based solar-pattern feature |

The earlier audit rebuilt the CSV from the source workbooks and checked continuity, duplicate timestamps and missing values. Those checks support data consistency; they do not establish independent model retraining.

The dataset does not include electrical topology, bus-level measurements, reactive power, outages or a genuine issued-weather archive. Reported production is not automatically unconstrained available renewable power; it can reflect curtailment or other operating effects. Likewise, measured demand may be affected by interruptions. Keep these meanings distinct when generating abnormal simulated scenarios.

### Other datasets

OPSD is an optional later generalization dataset, not a mandatory initial dependency. Using it requires coherent demand/solar/wind series, matching geography and timestamps, suitable capacities, rebuilt features, retraining and new evaluation.

NSRDB and WIND Toolkit are not required by the inspected ERCOT notebooks. Do not combine public datasets merely because they are available; geography, units, timing and aggregation must match.

## 7. Inputs and preprocessing

### Common data preparation

1. Read source wind and solar sheets and convert numeric fields.
2. Interpret local timestamps using America/Chicago, including daylight-saving ambiguity.
3. Convert to UTC, sort and check duplicates and hourly continuity.
4. Join source records one-to-one by timestamp and check agreement of demand values.
5. Validate missing/invalid numeric values and negative renewable production/capacity.
6. Calculate net load and derive calendar/proxy features.
7. Fix chronological split boundaries.
8. Fit learned preprocessing on training data only.
9. Build historical windows that exclude the target observation.

The active reference preparation validates invalid input rather than automatically interpolating gaps or deleting unusual high-demand events. Huber loss is not an outlier-cleaning procedure.

### Target-specific inputs

| Predictor | Released inputs | Network input shape |
|---|---|---|
| Demand | Historical demand plus one-hot local hour, day of month, month and year | 24 rows × 72 features |
| Wind | Historical wind generation, installed wind capacity and the same calendar encoding | 24 rows × 73 features |
| Solar | Capacity-factor history, proxy, lagged values and cyclical calendar features | 24 rows × 15 features |

The feature counts include encoded calendar columns; they are not counts of independent physical sensors. Historical net load is not required by the indirect component predictors.

Numeric input and target standardizers are fitted using training rows. Encoders are fitted on training data and handle unknown categories. The same fitted objects transform validation/test data and future inference inputs. Forecasts must be inverse-transformed before reporting MW metrics.

### Solar-specific preparation

The solar branch predicts a capacity-factor residual rather than directly predicting MW:

```text
Capacity factor = solar generation / installed solar capacity
Training target = target-hour capacity factor - capacity factor 24 hours earlier
Forecast capacity factor = earlier capacity factor + predicted residual
Forecast solar MW = forecast capacity factor × known target-hour capacity
```

The reference clips capacity factors to 0–1.05, with a small denominator epsilon. Its 15 input channels comprise capacity factor and proxy; their 1, 2, 24 and 48-hour lags; sine/cosine encodings of local hour and day of year; and a daylight indicator.

The proxy is `max(sin(pi × (local_hour - 6) / 12), 0)`. It is a fixed clock-based curve, not measured irradiance, cloud information or a physical clear-sky model.

The 24-row solar window contains 48-hour lagged features, requiring **72 raw hours of history**. Demand and wind require 24 hours. The initial complete service should require the full 72-hour history.

The reference gives more training weight to solar examples with meaningful production or large residual changes. These sample weights are not pretrained network weights.

### Weather decision

The paper discusses weather, but the active released notebooks reviewed here use history, calendar, capacities and the proxy. Weather is not required for the initial reproduction. Adding temperature, wind or irradiance is a named extension that must be evaluated separately. Future weather inputs must be forecasts issued before the power forecast, not observations collected afterward.

## 8. Split and training protocol

The reference fixes raw-time boundaries using approximately **90% training, 5% validation and 5% testing**, then assigns windows by target time. It does not randomly split time observations.

| Partition | Demand/wind examples | Solar examples | UTC target period |
|---|---:|---:|---|
| Training | 31,534 | 31,486 | Demand/wind start 2 January 2021 06:00; solar starts 4 January 2021 06:00; both end 8 August 2024 03:00 |
| Validation | 1,753 | 1,753 | 8 August 2024 04:00–20 October 2024 04:00 |
| Test | 1,754 | 1,754 | 20 October 2024 05:00–1 January 2025 06:00 |

Different training counts arise from different history requirements. Validation and test target timestamps remain aligned. Historical context may cross a split boundary; fitting model parameters or preprocessing on held-out targets is not allowed.

The final test covers about 73 days, principally late autumn and early winter. First reproduce this split, then add a separately reported chronological evaluation spanning seasons. Do not tune repeatedly on the final test set.

## 9. Leading architecture and training settings

These settings describe the previously inspected code, not an independently retrained GridMind model.

| Setting | Demand and wind | Solar residual predictor |
|---|---|---|
| First LSTM | 128 units, return sequence | 64 units, return sequence |
| First dropout | 0.20 | 0.15 |
| Second LSTM | 64 units | 32 units |
| Dense hidden layer | 64 units, ReLU | 32 units, ReLU |
| Second dropout | 0.20 | 0.10 |
| Output | One linear scalar | One linear residual |
| Optimizer | Adam | Adam |
| Initial learning rate | 0.0002 | 0.001 |
| Loss | Huber on standardized target | Huber on standardized residual |
| Maximum epochs | 100 | 80 |
| Batch size | 64 | 64 |
| Training shuffle | False | False |

Early stopping uses validation loss, patience 10 and restoration of the best weights. Learning-rate reduction halves the rate after four non-improving epochs, with a minimum of 1e-6. The reference sets random seeds to 42. Maximum epochs are limits, not guaranteed actual training durations.

The FCNN comparator flattens the history window and uses Dense 256/ReLU, dropout 0.30, Dense 256/ReLU, dropout 0.20 and a scalar output. Its reference solar target differs from the LSTM residual formulation. Reproducing these pipelines does not isolate architecture alone; a model-family-only comparison must equalize available information and target transformations where feasible.

### Weights and environment

No supplied pretrained checkpoint was verified in the inspected ERCOT release. Saved prediction files are not trained weights. Train from scratch, then save networks and fitted preprocessing. Fine-tuning is not required for this first implementation.

The authors recommend Python 3.9 and provide dependencies including TensorFlow/Keras. Establish and test an isolated environment before a full training run. CPU execution is described by the author instructions, but local runtime, memory requirements and complete dependency compatibility have not been measured here.

## 10. Outputs and physical constraints

Proposed service fields:

| Field | Meaning |
|---|---|
| `forecast_id` | Unique record identifier |
| `issued_at_utc` | Forecast issue time |
| `target_time_utc` | Forecasted hourly target |
| `horizon_hours` | 1 |
| `region_id` | Source/control-area identifier |
| `demand_mw` | Demand forecast |
| `solar_mw` | Solar forecast |
| `wind_mw` | Wind forecast |
| `net_load_mw` | Demand minus solar minus wind |
| `model_version` | Version of the complete predictor bundle |
| `data_quality_status` | Complete, reconstructed-input, fallback or unavailable status |

This is a proposed integration contract, not a published paper schema or an implemented API.

Reference postprocessing clips demand below at zero and wind to 0–1.05 times target-hour installed capacity. Solar reconstruction uses the corresponding capacity-factor bound. The 5% allowance is an author implementation choice, not a universal physical limit.

Capacity used for forecast reconstruction or clipping must be known at issue time. If only last-known capacity is available, use a documented policy and reevaluate. Do not silently use a retrospective future update.

## 11. Role in the five-function system

| Function/process | Responsibility | Relationship to forecasting |
|---|---|---|
| Demand and Renewable Forecasting | Estimate next-hour power values | Supplies forecasts and timestamps |
| Missing Telemetry Reconstruction | Estimate absent measurements while equipment remains operational | May supply explicitly marked historical estimates under a defined input policy |
| Abnormal Event Diagnosis | Distinguish supported data-quality issues and physical events; localize when identifiable | Does not replace forecasting or ordinary limit checks |
| Cascade-Risk Prediction | Assess propagation after an initial disturbance under defined assumptions | A separate target, not derivable from net load alone |
| Corrective-Action Recommendation | Suggest/rank supported interventions | May use future-state analysis; actions require simulated validation |
| Shared network analysis | Map profiles, run power flow and check configured limits | Ordinary Python/pandapower integration, not a sixth AI model |

Reconstruction must not turn a physical outage into an assumed missing sensor value. If reconstructed history is accepted by the forecasting service, preserve its provenance and evaluate that use separately from the clean-data reference experiment. Never silently substitute estimates and label them measured observations.

## 12. Forecast-to-network integration

The forecasting model does not learn “Line A will be overloaded.” The downstream process:

1. Copies the relevant simulated grid state.
2. Maps aggregate demand forecasts to loads using declared allocation shares.
3. Maps renewable forecasts to simulated generators using coherent scaling/capacity-factor rules.
4. Applies explicit conventional-generation, storage, equipment-status and reactive-power assumptions.
5. Runs the electrical calculation.
6. Compares line/transformer loading and bus voltage with configured limits.
7. Passes findings to the dashboard and relevant decision-support functions.

For example, the forecast may be demand 1,000 MW, solar 200 MW and wind 100 MW. The downstream calculation may then find Line A at 106% of its limit. **The 106% is a network-analysis result, not a forecasting-model output.**

For the first integrated demonstration, replay held-out ERCOT profiles in their source domain and transform actual and predicted profiles consistently for the benchmark network. Derive scaling references using training data and declared benchmark capacities. Allocations are simulation assumptions, not independently measured bus-level forecasts.

Do not feed small-network MW values directly into a model trained on ERCOT totals and assume transfer. Retraining is needed for a new coherent prediction domain unless a separately validated transfer method is adopted.

A converged power flow does not prove feasible dispatch or real-world safety. Generation limits, balancing, losses and other modeled constraints matter. Non-convergence or infeasibility must remain unresolved in the display, not be labelled safe. A predicted violation under one scenario is not a calibrated probability of failure.

The team must assign ownership of this integration code. Its existence does not automatically expand the forecasting student's AI training task into component-risk prediction.

## 13. Evaluation and model selection

### Required comparisons

- Persistence: latest observed value.
- Daily seasonal persistence: value 24 elapsed hours earlier.
- Weekly seasonal persistence: value 168 elapsed hours earlier.
- Indirect FCNN.
- Indirect LSTM.
- Optional gradient-boosted tree method if time permits.

Include an appropriate capacity-factor seasonal solar baseline for the residual model. Exact elapsed-hour lags can differ from the same local clock hour across daylight-saving transitions.

### Metrics

Report demand, solar and wind separately, followed by derived net load:

| Metric/check | Purpose |
|---|---|
| MAE in MW | Average absolute error |
| RMSE in MW | Greater emphasis on large errors |
| R² | Supporting measure of explained variation |
| Explicitly defined normalized/percentage errors | Comparability with stated denominator and masks |
| Persistence skill | Improvement over a simple baseline |
| Seasonal, peak and ramp breakdowns | Performance beyond one average |
| Runtime and model size | Practical implementation tradeoff |
| Save/reload consistency | Reproducible inference |

Solar percentage errors require special treatment near zero. Report all-hour MW errors and clearly defined daylight/production-mask errors. R² is not “percentage accuracy,” and MAPE should not be converted into 100 minus MAPE as an accuracy claim.

Net-load errors can hide component errors through cancellation. The selection must retain all three component scores. Where feasible, use several fixed random seeds and report variation after the initial reference reproduction.

### Acceptance evidence

The initial module should demonstrate:

1. Valid data schema, time alignment and causal feature availability.
2. Training-only learned preprocessing and untouched final evaluation targets.
3. Saved and reloadable predictors with all required preprocessing metadata.
4. Separate-target results against meaningful baselines, with limitations visible.
5. Correct timestamp alignment and net-load arithmetic.
6. Explicit handling of missing history and unavailable forecasts.
7. Successful handoff to simulated network analysis with declared assumptions.

No fixed accuracy or runtime threshold has been approved. The research papers' scores are reference observations, not acceptance guarantees. If the neural model fails to beat a relevant baseline, report and investigate it rather than conceal the result.

## 14. Reference results and what has been verified

The previous audit recalculated scores from released ERCOT predictions. It did not retrain the networks.

| Released pipeline | Net-load RMSE, MW | Net-load MAPE | R² |
|---|---:|---:|---:|
| Direct FCNN | 2,290.75 | 7.1381% | 0.923015 |
| Indirect FCNN | 2,469.80 | 7.3978% | 0.910510 |
| Direct LSTM | 1,127.73 | 2.7295% | 0.981342 |
| Indirect LSTM | 938.10 | 2.4635% | 0.987089 |

| Released indirect-LSTM output | MAE, MW | RMSE, MW |
|---|---:|---:|
| Demand | 459.41 | 603.58 |
| Solar | 254.99 | 530.40 |
| Wind | 537.86 | 741.15 |
| Net load | 695.46 | 938.10 |

These are not GridMind's own trained-model results. They do not prove transfer performance, full-year robustness or superiority over untested model families. The best average pipeline did not have the lowest maximum percentage error at every comparison.

Earlier review findings include paper/code differences in weather inputs, learning rates and sample-count wording; capacity-at-issue-time uncertainty; a short final holdout; and absent released trained checkpoints. Preserve the exact reference version and document changes instead of claiming an unchanged reproduction after modifying the method.

## 15. Research shortlist and optional extensions

| Reference | Current role |
|---|---|
| ERCOT indirect neural forecasting | Primary implementation foundation for the one-hour task |
| Nature Communications: *Probabilistic day-ahead forecasting of system-level renewable energy and electricity demand* | Retained comparison and possible later day-ahead uncertainty extension |
| *A hybrid deep learning–ensemble model for accurate and explainable electricity demand forecasting in renewable energy communities* | Optional demand/XGBoost/hybrid comparison reference, not a three-resource solution |
| MT-Transformer coordinated wind–solar–load study | Secondary joint-learning reference; exact implementation access remains unresolved |

The Nature paper provides public processed data and code, but the earlier review found archive/code compatibility problems, joint-script syntax issues and unverified complete saved predictors. It uses a different forecasting task and should not silently replace the one-hour scope.

The community LSTM–XGBoost paper forecasts demand only. Its 15-minute sampling does not establish a clearly specified forecast lead time. Its public original dataset is distinct from a verified release of the exact cleaned experiment. It supports considering a tree comparator; it does not prove that a hybrid will improve all three GridMind targets.

Optional extensions, after the first milestone:

- Matching weather observations or issued forecasts.
- Improved calendar encoding and history-window experiments.
- A jointly trained multi-output model.
- Prediction intervals and uncertainty calibration.
- Day-ahead trajectories for planning.
- A new region/dataset and explicit generalization evaluation.
- Explainability for a suitable model.

None is mandatory merely because it appeared in an earlier brainstorming document. Public code is helpful, but an implementable paper can be used with adequate method detail and accessible data; absence of code increases reproduction effort.

## 16. Implementation sequence

1. Preserve the paper, code revision, source data and attribution.
2. Validate the environment with a small run.
3. Rebuild or verify the canonical dataset and split boundaries.
4. Train the separate indirect LSTM predictors.
5. Train the indirect FCNN comparison and calculate simple baselines.
6. Evaluate all outputs on common timestamps; select using validation and report final test results.
7. Save networks, scalers, encoders, feature order, lag definitions, capacity policy, time conventions, seeds and dependency versions.
8. Package a reusable forecasting interface.
9. Integrate source-domain replay and declared network mapping with the team.
10. Test the full forecast-to-network-analysis demonstration and document limitations.

Keep source notebooks and released predictions separate from regenerated outputs. A forecasting service should not require manually executing notebooks every time a forecast is requested.

## 17. Dashboard behavior

Show the three forecasts, derived net load, issue time, target time and model version. Clearly distinguish simulated observations, reconstructed estimates, predictions and network-analysis results.

The dashboard may compare forecast and actual values when the target observation becomes available. It must not label a forecast as measured data or display stale predictions as current.

Component warnings should explain that they depend on the mapped forecast and assumed future operating state. Candidate corrective actions are evaluated separately and remain subject to engineer review.

## 18. Open decisions and limits

Still to establish during implementation:

- Complete environment compatibility and measured training/inference cost.
- Independently retrained model performance and final selected configuration.
- Forecast issue timing and historical capacity availability policy.
- Exact missing/reconstructed-input policy and evaluated fallback, if any.
- Benchmark network, allocation shares, scaling references and dispatch assumptions.
- Ownership of network integration and shared interfaces.
- Team-agreed numerical acceptance thresholds, if required.

Out of scope for the initial forecasting module: bus/line risk labels, outage diagnosis, cascade prediction, action optimization, switching control, unrestricted fault detection, real SCADA integration, electromagnetic transients and claims about the whole Egyptian grid.

## 19. Proposal-ready wording

GridMind's Demand and Renewable Forecasting module will predict electricity demand, solar generation and wind generation one hour ahead using public hourly time series. The initial implementation will reproduce the released ERCOT indirect neural forecasting approach, with three separately trained predictors providing power forecasts in MW and net load calculated from their outputs. Indirect LSTM is the leading candidate and will be compared with indirect FCNN and persistence-based references using a common chronological evaluation protocol.

Initial inputs comprise target-specific historical power, calendar features, renewable capacities and the released solar proxy. Weather and joint learning are optional extensions. The initial predictors do not require electrical topology. Forecasts will support a separate integration process that maps future power profiles to a simulated transmission network and evaluates electrical conditions under explicit operating assumptions. GridMind remains a software-only decision-support prototype in which the engineer makes the final decision.

## 20. References and document status

- [ERCOT paper, version 2](https://arxiv.org/abs/2604.17012v2)
- [ERCOT implementation](https://github.com/rpglab/ML_ERCOT-NetLoad_Forecasting)
- [Nature Communications paper](https://doi.org/10.1038/s41467-026-69015-w)
- [Nature implementation](https://github.com/gterren/caiso_power)
- [Nature experimental archives](https://zenodo.org/records/16729434)
- [Community demand hybrid paper](https://doi.org/10.1016/j.enbuild.2026.117851)
- [Community original dataset](https://data.mendeley.com/datasets/vryvyfz2tj/1)

This file consolidates the decisions and prior research audits recorded in the chat through 30 October 2026. External resources were not re-audited when creating this Markdown file. Public repositories can change. The original project files remain background references and have not been edited by creating this document.
