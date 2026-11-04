# GridMind 10% POC Frontend Implementation Plan

**Proposal demonstration:** 10 November 2026  
**Document date:** 4 November 2026  
**Status:** Implementation plan; frontend implementation is not part of this document deliverable.  
**Source of authority:** [plan.md](plan.md), with the user's frontend-only and precomputed-export overrides described below.

## 1. Purpose, authority, and scope

Build a local, frontend-only dashboard for the proposal demonstration. Train forecasting and stage-1 event diagnosis in Google Colab, then display exported inputs, genuine predictions, baselines, and evaluation results. The browser performs no model inference.

This document supplements `plan.md`; it does not replace, remove, or edit it. It describes future frontend work only.

### Authority and overrides

Use this precedence:

1. The latest user instruction: frontend only, no backend, exported predictions.
2. The explicit overrides at the top of `plan.md`.
3. Other applicable sections of `plan.md`.
4. Referenced model specifications, where compatible with the POC overrides.

Model references:

- [Demand and renewable forecasting](Model_Documentation/GridMind_Demand_Renewable_Forecasting.md)
- [Event diagnosis](Model_Documentation/EVENT_DIAGNOSIS.md)
- [Whole-system overview](Model_Documentation/GridMind_Whole_System_Overview.md)
- [Missing telemetry](Model_Documentation/GridMind_Missing_Telemetry_Complete_Research_and_Model.md)
- [Cascade risk](Model_Documentation/GridMind_Cascade_Risk_Prediction_Model.md)
- [Corrective actions](Model_Documentation/GridMind_Corrective_Action_Model.md)

| Conflict or missing information | Frontend decision |
|---|---|
| `plan.md` specifies FastAPI, local inference, and API endpoints | Replace these with static JSON/CSV exports and local asset loading. Do not implement the API or browser-based XGBoost inference. |
| Existing workflow says to generate forecasts and run diagnosis locally | Controls select and reveal genuine exported results. Label them **Precomputed model predictions**. |
| Older forecasting sections recommend full-data and other splits | Follow the top-level override: 17,544 contiguous sampled hours, 168-hour warmup, and 13,900/1,738/1,738 chronological target examples. |
| Model specifications describe neural architectures and diagnosis localization | Use XGBoost exports only. Stage-2 localization is excluded. |
| Whole-system documents describe electrical analysis and validated actions | Use explicitly scripted demonstrations. No power flow, physical validation, or automatic forecast-to-network mapping. |
| Diagnosis dataset, channels, units, cadence, and parent families are unresolved | Treat these as export-readiness blockers. Do not select a replacement dataset or invent measurements. |
| Simulation topology and scenario fixtures are not supplied | Author small, versioned illustrative fixtures, reviewed by the relevant model owners. They are demonstration content, not research results. |
| Existing forecasting artifacts were executed locally | They are reference material and possible export inputs. Do not describe them as a completed Colab run. |
| README mentions approximately 100 seconds; the current forecasting run manifest records 76.48 seconds | Display runtime from the selected run's manifest, with its environment and scope. Do not mix measurements from different runs. |

**Included:** five dashboard views, static artifact loading, replay controls, three deterministic simulations, provenance, evaluation, and an approximately seven-minute walkthrough.

**Excluded:** backend services, live feeds, user-uploaded inference, equipment control, normal-operation detection, physical-event localization, weather, neural models, databases, authentication, and electrical simulation.

The target is **two trained capabilities**, comprising **four estimators**: three forecasting regressors and one diagnosis classifier. This target is not a claim that diagnosis training is complete.

## 2. Dashboard structure and layouts

Use the five views already specified in `plan.md`. Keep navigation visible on desktop and available through a compact menu on smaller screens.

A persistent header contains the active demonstration scenario, **Offline replay** indicator, play/pause and step controls, Reset, and the active time basis. A persistent legend explains provenance.

### Overview

Purpose: explain the POC and provide a reliable demonstration starting point.

- Five capability cards: forecasting, event diagnosis, reconstruction, cascade risk, and corrective actions.
- Cards show availability, the relevant result summary, and its provenance badge.
- An illustrative 14-bus SVG network occupies the main area.
- A side panel shows scenario description, linked replay selections, source domains, and limitations.
- Network selection opens an inspector with component ID, type, equipment status, available measurements, and simulation state.
- Forecast cards show aggregate ERCOT MW; they do not imply measurements at individual illustrated buses.
- Diagnosis category does not automatically highlight a failed component.

Show **Illustrative 14-bus network; not the measurement network for ERCOT or event data.**

### Forecasting

Purpose: replay genuine one-hour-ahead forecasts and compare them with observations and baselines.

- Summary cards for demand, solar, wind, and calculated net load.
- Separate demand, solar, and wind charts; an additional net-load panel.
- Historical observations end at the selected issue time.
- The forecast marker appears at the target time, exactly one hour later.
- Reveal Actual exposes the exported target observation and calculated error.
- Baseline selector: last observation, daily persistence, weekly persistence, and solar daily capacity-factor persistence where exported.
- A details panel shows issue time, target time, region, model version, history requirements, capacity policy, and quality warnings.
- A compact table provides the plotted values for accessible inspection.

Show **Calculated from precomputed model predictions** on forecast net load. Do not display prediction intervals unless the exported run includes supported intervals and their method.

### Event diagnosis

Purpose: inspect window-level classification of held-out abnormal episodes.

- Episode selector, with filters for physical examples, sensor examples, and explicit unsupported-input examples.
- Electrical traces grouped by compatible units.
- Visible observation-window boundaries.
- Result card: sensor problem, physical event, or uncertain/unavailable with reason.
- Exported raw XGBoost score and threshold, when present.
- Ground-truth label and correctness comparison presented separately from the prediction.
- Measurement table with channel, source component ID, unit, quality, and original reading.
- Provenance panel identifies real, source-simulated, or controlled-corruption inputs.

State that classification uses the **complete exported abnormal window**. Moving a cursor through its trace does not rerun diagnosis or imply real-time event detection.

Always show **Physical location unavailable — stage 2 excluded.**

### Scenario laboratory

Purpose: demonstrate the three simulated capabilities without implying trained inference.

Use three panels or subtabs:

| Panel | Components and behavior |
|---|---|
| Reconstruction | Original/reference trace, masked readings, separate missingness mask, illustrative reconstructed trace, and equipment status |
| Cascade | Hypothetical outage selector, stress preset, propagation-round controls, network animation, affected-component table, qualitative severity, and optional scripted DNS |
| Corrective actions | No-change, redispatch, and renewable-curtailment candidates; affected assets; MW changes; before/after loading and voltage where supplied; unsuccessful example |

Every panel displays **Simulated demonstration**.

Action comparisons also display **Illustrative outcome; physics validation not implemented.** Use **Compare illustration**, not Execute, Dispatch, or Apply to grid.

### Evaluation and provenance

Purpose: show what was actually evaluated and where every displayed result came from.

- Forecast metrics and baseline comparisons by target and exported subset.
- Diagnosis confusion matrix, macro-F1, balanced accuracy, per-class precision/recall, and physical-event miss rate.
- Actual split boundaries and sample counts.
- Diagnosis counts for raw rows, episodes, and independent parent families.
- Model/run versions, source hashes, feature-policy summaries, training environment, and measured runtimes.
- Exclusions, unsupported cases, and model-card limitations.
- Clear distinction between held-out metrics and errors on the currently selected replay example.

If diagnosis evaluation is absent, show its blocker. Do not substitute paper results or simulation outcomes.

## 3. User interactions and scenario coordination

### Shared state

Use one application state containing:

```text
activeView
scenarioId
forecastReplayId
eventEpisodeId
laboratoryScenarioId
activeTimeline: forecast | event | laboratory
timelinePosition
isPlaying
actualRevealed
selectedComponentId
selectedChannels
selectedForecastSeries
baselineMethod
missingnessPresetId
contingencyId
stressPresetId
actionId
```

Keep loaded artifact data separate from interaction state. Retain a position for each timeline so switching views does not accidentally transfer a forecast-hour index to an event-sample index.

### Scenario selection

The scenario catalog coordinates a demonstration bundle through explicit references to:

- A forecasting replay window and default issue record.
- An event episode, if available.
- A separate illustrative laboratory scenario.
- Defaults and supported controls.

These references organize the presentation. They do **not** establish that an ERCOT hour, event episode, and illustrated outage represent the same physical occurrence.

On scenario change:

1. Pause playback and clear old result selections.
2. Load and validate referenced assets.
3. Commit the new scenario and defaults together.
4. Update cards, charts, tables, network overlays, and provenance from that committed selection.
5. Show explicit unavailable panels for missing capabilities.

Ignore late responses belonging to a previously selected scenario. Never leave old predictions beside a new scenario label.

### Timeline behavior

- **Forecast timeline:** step between exported issue records. Playback selects successive records; it never generates new forecasts.
- **Event timeline:** move through the exported trace. The classification remains associated with its complete observation window.
- **Laboratory timeline:** advance through scripted propagation rounds.
- Use one playback controller at a time. Navigation pauses playback.
- Default playback advances one exported step per second and stops at the end.
- Previous/Next and keyboard-accessible timeline controls remain usable with playback stopped.
- Reset restores the selected scenario's defaults, hides target actuals, clears component inspection, and returns all timelines to their starting positions.

### Filtering and inspection

- Forecast series toggles alter visibility only.
- Event filters select episodes or channels; they do not change the exported prediction.
- Network/table selection shares the same selected component within the illustrative network.
- Dataset component IDs stay in their own namespace. Do not invent a mapping to illustrated buses.
- Measurement tables support component/channel and provenance filters.
- Cascade controls expose only fixture-supported combinations.
- Changing an outage or stress preset resets cascade progression and clears the previous action comparison.
- Missingness controls affect laboratory telemetry only; they never modify forecasting or diagnosis inputs.
- Unsupported combinations show Unavailable with a reason.

## 4. Static data contracts

The following are **proposed frontend integration contracts**, derived from the model specifications. They are not claims about an existing API or completed exports.

Use JSON as the browser-facing format. Keep CSV exports for reproducibility and inspection. Convert existing CSVs to JSON during export preparation rather than implementing a general CSV-import feature in the dashboard.

### Common metadata and provenance

Every artifact must carry, or reference through its manifest:

| Field | Requirement |
|---|---|
| `schema_version`, `bundle_id`, `artifact_version` | Identify the contract and compatible export bundle |
| `record_id` | Stable unique record identifier; domain-specific IDs such as `forecast_id` fulfill this role |
| `dataset_id`, `source_id` | Identify the actual source; not a fabricated benchmark association |
| `model_version`, `run_id` | Required for genuine predictions; absent for purely scripted outputs |
| `exported_at_utc` | Export time, distinct from measurement or prediction time |
| `source_sha256` | Hash of the underlying source or referenced source manifest |
| `split` | Train, validation, test, or explicitly not applicable |
| `provenance_kind` | Observed, dataset input, synthetic input, precomputed prediction, calculated, simulated, or unavailable |
| `limitations`, `quality_status` | Relevant warnings and availability |
| `units` | Field/channel unit definitions |
| `origin` | Real measurement, source simulation, controlled corruption, or authored illustration |

Use ISO 8601 UTC timestamps with explicit offsets. Retain hour-ending semantics for ERCOT. Default dashboard timestamps to UTC; use `America/Chicago` only when explicitly displaying source-local time. Cairo time applies to the demonstration schedule, not source measurements.

For event data without trustworthy absolute timestamps, export elapsed time plus the declared source time basis. Do not manufacture calendar dates.

Use `null` plus a reason for unavailable values. Zero is a valid measurement. Reject non-finite numbers.

### Catalog and bundle manifest

`catalog.json` contains:

- Bundle/schema version and default scenario.
- Scenario IDs, titles, descriptions, and explicit cross-view references.
- Forecast replay IDs, available event episode IDs, and laboratory scenario IDs.
- Asset paths, asset status, and default control selections.

`bundle_manifest.json` contains:

- Per-file path, version, checksum, and producing run or fixture version.
- Dataset/source references, model versions, generation environment, and limitations.
- Capability availability and reasons for blocked capabilities.
- Links to evaluation, feature, split/group, and model-card artifacts.

Do not combine prediction files and evaluation reports from incompatible runs.

### Forecast observations

`forecast_observations.csv`, mirrored as JSON, retains the documented source columns:

```text
time
total_load
solar_generation
solar_installed
wind_generation
wind_installed
net_load
clear_sky_proxy
```

Power and capacity are MW; proxy is dimensionless.

Export at least 168 consecutive context hours preceding and including the first selected replay issue time, plus the replay interval and target observations. Distinguish historical context from held-out target examples.

### Forecast predictions

`forecast_predictions.json` contains records with:

```text
forecast_id
issued_at_utc
target_time_utc
horizon_hours
region_id
history_start_utc
history_end_utc
history_rows
split
demand_mw
solar_mw
wind_mw
net_load_mw
model_version
run_id
data_quality_status
capacity_policy
provenance metadata
```

Requirements:

- `horizon_hours` is 1; target time is exactly one hour after issue time.
- History ends no later than issue time.
- Demand/wind require 24 hours, solar 72 hours, and the weekly comparison 168 hours.
- Net load equals demand minus solar minus wind.
- Export final postprocessed MW outputs.
- Preserve the documented solar residual transformation and last-known-capacity policy in the feature manifest.
- The frontend does not rebuild features, reconstruct solar forecasts, or reapply clipping.

`forecast_baselines.json` joins through forecast ID and target time. It contains method, target, value in MW, and eligibility status.

Actual observations remain separate from predictions. Reveal Actual is a presentation control, not protection against inspecting bundled files.

### Event episodes and predictions

`event_episodes.json` is the episode index. Each episode declares:

```text
episode_id
parent_family_id
dataset_id
split
ground_truth_class
input_origin
trace_path
observation_window
time_basis
sample_interval
sample_count
channel_definitions
quality_status
limitations
```

Each channel definition contains:

```text
channel_id
source_component_id
quantity
unit
```

Trace files use timestamps or elapsed offsets and channel values. Preserve original readings. Export corruption metadata separately: parent episode, affected channels, type, interval, severity, and seed. Do not expose that metadata as classifier input.

`diagnosis_predictions.json` contains:

```text
prediction_id
episode_id
status
predicted_category
raw_score
score_class
decision_threshold
class_mapping
observation_window
diagnosed_at_utc
model_version
run_id
physical_location
reason
provenance metadata
```

Rules:

- Export class encoding and score meaning; do not assume which class is positive.
- Threshold selection follows validation macro-F1 with the physical-recall tie-break in `plan.md`.
- An uncertain result for invalid/unsupported input is a policy outcome, not a third trained class.
- `physical_location` remains unavailable.
- Diagnosis time is the original computation time, not the browser replay time.
- Display raw scores as uncalibrated model scores unless calibration evidence is exported.
- Do not infer diagnosis from the visible trace using frontend rules.

### Evaluation artifacts

`forecast_metrics.csv` retains the existing useful structure:

```text
target,split,group,method,mae_mw,rmse_mw,r2,n,mae_skill_vs_persistence
```

Include exported daylight, seasonal, peak, and ramp subsets where available. Empty groups are unavailable, not zero-error results.

`diagnosis_evaluation.json` includes:

- Metric definitions and values.
- Confusion matrix with explicit row/column class order.
- Majority-class baseline.
- Episode and independent-family counts by split/class.
- Grouping policy, exclusions, and semi-synthetic limitations.
- Bootstrap intervals only if actually calculated, including method and resampling unit.

Export split/group manifests and model cards alongside these results.

### Illustrative network and simulations

These files are authored demonstration fixtures, not required Colab training exports.

`network.json` contains:

- Network ID/version and illustrative designation.
- Fourteen bus nodes with stable IDs and SVG coordinates.
- Lines/transformers with endpoint IDs.
- Generators/loads with their connected bus IDs.
- Equipment status independent of measurement availability.

Use namespaced IDs such as `illustrative14:bus:01`. Source-event IDs remain source-event IDs.

Laboratory fixtures contain:

| Capability | Required content |
|---|---|
| Reconstruction | Reference values, original/displayed values, separate missingness mask, equipment status, selected reconstruction values, channel units |
| Cascade | Explicit hypothetical initiating component, supported stress presets, ordered rounds, affected component IDs, qualitative severity, assumptions |
| Actions | No-change/redispatch/curtailment candidates, affected assets and MW changes, before/after fixture values, illustrative outcome and explanation |
| Optional DNS display | Scripted fraction in 0–1; MW only when a declared illustrative baseline demand supports conversion |

For reconstruction, support bus voltage magnitude and line-end active/reactive power where fixture data is supplied. Use pu, MW, and MVAr explicitly. Do not derive current/loading without coherent fixture quantities and ratings.

Never reconstruct a healthy operating reading for out-of-service equipment. Unknown equipment status produces an explicit unavailable/uncertain illustration.

Represent simulated action validation as **not implemented**. Do not populate successful power-flow or engineering-check results.

## 5. Colab export checklist and integration gates

### Required before forecasting integration

- [ ] Genuine three-regressor predictions for a held-out replay window: `forecast_predictions.json`.
- [ ] Observation/context rows and target actuals: `forecast_observations.csv` and `.json`.
- [ ] Last-observation, daily, weekly, and solar daily capacity-factor baselines: `forecast_baselines.json`.
- [ ] Forecast metrics: `forecast_metrics.csv` and a browser-ready JSON counterpart.
- [ ] Split manifest, run manifest, feature policy, model version, limitations, and source hashes.
- [ ] Browser-ready catalog entries and bundle manifest linking the same run.

Use the first 168 consecutive held-out target hours as the initial replay window, provided the export validates. Retain the required preceding context. The selector must not present training examples as held-out predictions.

Existing local `reports/forecasting` outputs can seed export preparation, but require provenance-preserving conversion and verification. In particular, `predictions.csv` contains multiple partitions and must be filtered explicitly. Use `example_forecast.json`, `metrics.csv`, `split_manifest.csv`, and `run_manifest.json` as existing references, not evidence that the new browser bundle already exists.

### Required before diagnosis integration

- [ ] Inspected, defensible dataset with resolved labels, channels, units, cadence, and episode boundaries.
- [ ] Parent-family identifiers and group-separated split manifest.
- [ ] Episode index and original trace files: `event_episodes.json` plus referenced trace JSON/CSV.
- [ ] At least one held-out physical episode and one held-out sensor example.
- [ ] Genuine classifier outputs: `diagnosis_predictions.json`, including score class, class mapping, selected threshold, and model version.
- [ ] Any controlled-corruption provenance and recipes, separate from model inputs.
- [ ] `diagnosis_evaluation.json`, including metrics, confusion matrix, majority baseline, independent-family counts, and limitations.
- [ ] Explicit invalid/unsupported-input examples, identified as policy demonstrations rather than trained results.

If compatible sensor data or defensible labels are unavailable, mark diagnosis blocked. This prevents acceptance of the intended two-trained-capability demonstration; it does not prevent showing the forecasting page.

### Research archive, outside browser assets

Preserve executed notebooks, reusable Python source, native model files, preprocessing/configuration artifacts, exact package versions, parameters, and training hardware.

The frontend needs predictions and evidence, not model weights or Python runtime dependencies.

## 6. Output presentation rules

| Content | Required visible presentation |
|---|---|
| ERCOT history/actuals | **Observed — ERCOT dataset** |
| Event traces | **Dataset input**, plus actual source origin |
| Controlled-corruption input | **Synthetic sensor corruption** |
| Forecasts and stage-1 diagnosis | **Precomputed model predictions** |
| Forecast net load | **Calculated from precomputed model predictions** |
| Baselines and errors | **Calculated**, with method/formula |
| Reconstruction, cascade, actions | **Simulated demonstration** |
| Missing output | **Unavailable**, with reason |

Apply provenance to cards, chart legends/tooltips, tables, and comparison panels. It must remain visible in screenshots.

Use line style and symbols as well as color:

- Observations: solid line.
- Predictions: distinct dashed line and target marker.
- Simulated reconstruction: separate patterned/dashed trace.
- Missing samples: visible gaps; do not connect them as observed data.
- Unavailable values: text and an explanation.

Do not show invented confidence percentages, forecast bands, risk probabilities, or accuracy percentages derived from regression errors. Aggregate metric intervals are not individual-prediction confidence.

## 7. Frontend architecture and data flow

Retain **React, TypeScript, Vite, Recharts, and SVG** from `plan.md`. Use plain CSS with shared design tokens and system fonts. No external asset/CDN dependency.

Suggested structure:

```text
frontend/
  public/data/
    catalog.json
    bundle_manifest.json
    forecasting/
    diagnosis/
    scenarios/
    evaluation/
  src/
    app/
    views/
    components/
    data/
    state/
    simulations/
    styles/
  tests/
```

Reusable components include:

- Application shell and scenario selector.
- Provenance badge and source details.
- Metric card and availability panel.
- Timeline controls.
- Time-series chart and accessible value table.
- SVG network and component inspector.
- Measurement table.
- Diagnosis result and confusion matrix.
- Action-comparison table.

Use React Context plus `useReducer` for coordinated state. Derive net load, visible rows, selected records, and network overlays through selectors rather than duplicate state.

Load through a typed static-data repository:

```text
Bundled assets
→ runtime validation
→ normalized read-only records
→ scenario selectors
→ shared state
→ views/components
```

- Fetch the catalog and manifest first.
- Load referenced assets on demand and cache successful loads.
- Use paths compatible with Vite's configured base URL.
- Validate required fields, finite values, timestamps, identifiers, references, and supported schema versions.
- Show component-level failures when only one capability is affected.
- Provide retry for failed asset loads.
- Never replace missing genuine predictions with demonstration fixtures.
- Keep deterministic simulation functions isolated from model-result selectors.

Serve the built dashboard through a local static server. It is not an application backend. Do not promise double-click `file://` support or add a service worker for this POC.

Use Vitest for data/state logic and a small Playwright browser suite. These are implementation choices supporting the existing smoke-test requirement. Pin tested dependency versions when implementation starts; no particular current version is assumed here.

## 8. Visual design and operational states

Use a professional control-center appearance with dark navy navigation, neutral chart surfaces, restrained accents, and readable numeric typography.

- Prioritize scenario name, provenance, current selection, and result status.
- Keep units beside values and chart axes.
- Use separate axes/panels for incompatible electrical units.
- Use consistent target colors across cards and charts.
- Pair status colors with text/icons; do not rely on red/green alone.
- Distinguish missing telemetry, equipment outage, and unknown equipment status visually.
- Support keyboard navigation, visible focus, labeled controls, and accessible tables.
- Respect reduced-motion preferences.
- Use stable SVG geometry; avoid force-layout movement during the demonstration.

Target the presentation laptop first: verify at 1366×768. Collapse multi-column layouts below 1024 px and use single-column panels below 768 px. Allow horizontal scrolling within wide tables rather than shrinking labels.

Required states:

- **Loading:** reserved chart/card space and a clear loading message.
- **Empty:** no matching episode/channel, with a filter-reset action.
- **Unavailable:** missing artifact, unsupported combination, or excluded capability with reason.
- **Error:** affected asset and validation/load failure, with retry where meaningful.
- **Partial:** available capabilities remain usable while blocked capabilities retain explicit status.

## 9. Prioritized milestones and acceptance criteria

Dates are proposed targets in Cairo time, not claims that earlier schedule items are complete.

| Priority / target | Work and dependency | Acceptance criterion |
|---|---|---|
| P0 — 4–5 Nov | Freeze static contracts; inventory existing forecasting artifacts and diagnosis blockers. Integration lead and model owners review. | Export checklist, provenance rules, class/feature metadata requirements, and blocker list agreed; backend requirements explicitly superseded for this frontend scope. |
| P0 — 5 Nov | Build shell, five-view navigation, shared scenario state, and loading/error components. Uses visibly marked development fixtures. | Navigation, scenario selection, reset, and unavailable states work without stale content. |
| P0 — 6 Nov | Produce and verify Colab export bundles. Depends on dataset gates and frozen model choices. | Forecast replay and two diagnosis example classes join to genuine predictions, reports, and manifests; missing gates remain visible blockers. |
| P0 — 7 Nov | Integrate forecasting and diagnosis pages, evaluation, and provenance. | Charts match exports; next-hour alignment, actual reveal, raw-score meaning, class mapping, and split counts are correct. |
| P1 — 7 Nov | Integrate three laboratory demonstrations, reviewed by model owners. | Missingness remains separate from equipment status; outage is explicitly hypothetical; all three action types and an unsuccessful example are inspectable. |
| P0 — 8 Nov | Feature freeze and verification on presentation laptop. QA owns evidence. | Build and browser checks pass; no external runtime requests; no unlabeled fabricated outputs; missing artifacts produce explicit states. |
| P1 — 9 Nov | Two complete rehearsals and backup preparation. | Each walkthrough finishes in approximately seven minutes; reset restores the starting state; screenshots and backup recording retain provenance. |
| 10 Nov | Present frozen build. | No training, dependency changes, or artifact replacement during discussion. |

Retain the ownership in `plan.md`: Member 1 leads integration, Member 2 owns forecasting, Karim/Member 3 owns diagnosis, Member 4 owns frontend, and Member 5 owns QA/evaluation. Simulation review and dataset readiness require the relevant model owners; the frontend developer must not fabricate their missing evidence.

If time slips, remove optional extra scenarios, additional chart polish, and optional breakdown views first. Preserve genuine exports, readiness checks, provenance, evaluation, and error handling.

**Optional after acceptance:** additional reviewed replay windows and laboratory scenarios. These are not prerequisites for the proposal.

## 10. Verification and committee walkthrough

### Data and calculation checks

- Validate every catalog reference and component/channel ID.
- Check forecast target equals issue time plus one hour.
- Verify historical context and common baseline eligibility.
- Confirm replay predictions come from the declared held-out partition.
- Check net-load arithmetic and forecast/actual/baseline target alignment.
- Preserve numerical precision; document conversion tolerance when adapting existing rounded CSV outputs.
- Check complete event-window association, units, score class, threshold, and class mapping.
- Verify no parent family or related corruption crosses partitions.
- Check metric counts against split/group manifests.
- Confirm all reported runtimes and results belong to the selected run.
- Keep Colab prediction parity checks in export preparation; browser checks compare loaded values with frozen exports.

### Interaction checks

- Change scenarios during loading and confirm old responses cannot overwrite the new selection.
- Step and play each timeline; stop correctly at its final record.
- Reveal actuals, change forecast issue time, and confirm actuals are hidden again.
- Filter channels/episodes without changing the corresponding prediction.
- Confirm stage-1 diagnosis never creates a component location or initiating outage.
- Mask telemetry without changing equipment status or genuine model inputs.
- Change stress/outage and confirm cascade/action state resets.
- Compare no-change, redispatch, curtailment, and an unsuccessful illustration.
- Exercise missing files, malformed records, empty filters, and unsupported combinations.
- Reset twice and obtain the same default state.
- Verify keyboard access, responsive layout, readable charts, and reduced-motion behavior.
- Disconnect external networking and rehearse from the local static build.

### Seven-minute committee script

| Time | Demonstration |
|---|---|
| 0:00–0:40 | Explain two trained capabilities, four estimators, static replay, and three simulated capabilities. Show the provenance legend. |
| 0:40–2:10 | Select a held-out ERCOT hour; show three precomputed forecasts; reveal actuals; compare persistence and calculated net load. |
| 2:10–3:30 | Inspect one physical episode and one sensor example. Show genuine stage-1 predictions, raw-score qualification, input origin, and unavailable localization. |
| 3:30–5:20 | Explicitly open the separate laboratory scenario. Mask telemetry, select a hypothetical outage, advance propagation, and compare scripted actions. |
| 5:20–6:30 | Show actual forecast split periods, diagnosis independent-family counts, metrics, source/run provenance, and limitations. |
| 6:30–7:00 | Show unsupported/insufficient-input handling, reset, and state the remaining research work. |

Acceptance requires honest presentation of both trained components. If diagnosis training remains blocked, explain the reduced demonstration explicitly; simulation does not satisfy the missing trained-component requirement.
