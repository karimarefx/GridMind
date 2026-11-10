# GridMind local research dashboard

## Experimental upload service added

The current PoC supports local normal/abnormal detection followed by timing/physical
classification. From the repository root, install `requirements-api-lock.txt`,
build this frontend, set `PYTHONPATH` to `src`, then run `python -m gridmind.api`.
Open `http://127.0.0.1:8000`. In Vite development mode, `/api` proxies to that service.
The saved model runs in Python, not the browser. No public deployment is configured.

Upload prepared CSVs with exactly 1,800 original samples at 30 Hz and the seven
columns displayed in the form. Both angle columns use the selected unit. Files
are limited to 2 MiB and are not retained. The interface shows normal, physical,
PMU timing anomaly or uncertainty; it does not invent ground truth for uploads.

Combined grouped development returned only eight normal decisions out of 62
inputs, with 54 uncertain and zero returned cause diagnoses. The prototype is
experimental and not independently validated. Full measured results and source
limitations are in `../reports/diagnosis/stage1_summary.md`.

The static-only instructions below describe the original replay capability.
Running only Vite leaves upload inference unavailable until Python is started.

React + TypeScript + Vite + Recharts, with an interactive SVG network. Static files only: no backend, training, browser inference, or external runtime services. `plan.md` is unchanged; `frontend.md` remains the implementation reference.

## Run

Use Node.js 22.12+ (tested with Node 24) and npm. From this folder:

```powershell
npm ci
npm run dev
```

Open the localhost URL printed by Vite. For the production bundle:

```powershell
npm run build
npm run preview
```

The production build is in `dist/`. Keep the static server running while presenting; double-click `file://` loading is unsupported. Dependencies are needed for setup; the built dashboard needs no external network connection. Fonts, icons, charts and data are local.

## What is actually available

- **Forecasting:** 168 genuine held-out XGBoost records, starting at target `2024-10-20T20:00:00+00:00`, from the existing **locally executed** run `xgboost-sample-v1`. This is not represented as Colab execution. Model results are never fabricated or recomputed by the browser.
- **Diagnosis:** blocked. No inspected dataset, trained classifier, original episode traces, class mapping, threshold, or independent-event evaluation was supplied. The UI shows a readiness checklist rather than invented traces/results. Future valid episode exports are supported through the static contracts below.
- **Reconstruction, cascade and actions:** deterministic authored fixtures, explicitly labeled **Simulated demonstration**, awaiting model-owner review. They have no learned inference or electrical validation.

The target of two trained capabilities is **not yet met**. Colab training/export and diagnosis data readiness remain external prerequisites. No training or evaluation was newly performed by this frontend work.

## Reproduce the packaged data

Python's standard library is sufficient. These commands read existing research outputs and write only frontend data:

```powershell
python scripts/create_fixtures.py
npm run export:data
```

`export_data.py` verifies the supplied ERCOT file against the research run's SHA256, selects the first 168 test targets, preserves preceding 168-hour context, packages predictions/baselines/metrics, and writes a manifest with per-file checksums. Net load is explicitly calculated from the packaged component values because the source prediction CSV has rounded component precision.

**Do not run the export script over a newly installed Colab bundle:** it intentionally replaces browser data with the existing local forecast run and marks diagnosis unavailable. Run it only to reproduce this checked-in local baseline package. Re-run after changing authored fixtures so checksums are updated.

## Colab handoff

Produce JSON using the contracts in `../frontend.md`. Keep genuine numerical values and record the actual producing environment. Package:

| Folder | Required files |
|---|---|
| `forecasting/` | `forecast_predictions.json`, `forecast_observations.json` / `.csv`, `forecast_baselines.json` |
| `evaluation/` | `forecast_metrics.json`, `metrics.csv`, `split_manifest.csv`, `run_manifest.json`, limitations/model-card material |
| `diagnosis/` | `event_episodes.json`, `diagnosis_predictions.json`, `diagnosis_evaluation.json`, original trace JSON files, parent-family split/feature/corruption manifests |
| Data root | `catalog.json`, `bundle_manifest.json` with matching bundle/schema/run/model versions, origins and file hashes |

Keep native XGBoost models, source notebooks and preprocessors in the research archive, not browser assets. The dashboard does not execute them.

### Current browser contract details

Schema version is `"1"`. Catalog scenarios declare `id`, `title`, `description`, zero-based `forecast_start` and inclusive `forecast_end`, and `laboratory_id`. These indices select records in the single packaged forecast array; they are presentation bundles, not claims of physical correspondence between source datasets and the network. Current scenarios share the separately authored laboratory. The catalog's `default_scenario` must exist.

Predictions contain the fields listed in `frontend.md`; replay targets must be held-out test records, with one-hour issue/target alignment, a model version, capacity policy and at least 168 context rows for this replay package. `bundle_manifest.model_version` must match. Observations use the original ERCOT names, including `time`, `total_load`, `solar_generation`, `wind_generation`, `solar_installed`, `wind_installed`, `net_load`, and `clear_sky_proxy`.

An event episode contains `episode_id`, `parent_family_id`, `split: "test"`, `ground_truth_class: "physical" | "sensor" | "unsupported"`, `input_origin`, `trace_path` relative to the data root, `observation_window: {start, end}`, `time_basis`, `sample_interval`, `sample_count`, `channel_definitions` and `limitations`. Each channel declares `channel_id`, `source_component_id`, `quantity`, and `unit`. Trace files are row arrays: `elapsed_seconds` and channel-name keys when `time_basis` is `"elapsed_seconds"`; otherwise use `time` with actual source timestamps. Never invent absolute dates or component mappings.

Diagnosis predictions join by episode ID. They include prediction ID, status, category, raw score, score class, threshold, class mapping, observation window, model/run version, computation time, reason, and `physical_location: null`. Scores are uncalibrated unless exported evidence establishes otherwise. The event chart cursor and value table inspect samples; prediction remains associated with the complete window.

Diagnosis evaluation uses `status`, optional `reason`, `metrics` (named numeric values), `counts` (named episode/row/family counts), `class_order`, and `confusion_matrix` with actual rows and predicted columns. Add evaluated baseline and grouping details to research manifests. No intervals should be shown unless actually evaluated.

Replace and verify the complete compatible bundle before the demonstration; do not mix runs. Keep checksums current. Missing files and malformed/unsupported records must produce explicit unavailable states.

## Checks

```powershell
npm test
npm run test:e2e
npm run build
npm audit
```

Unit checks cover held-out exports, arithmetic, time alignment, context, invalid predictions, scenario resets and out-of-service reconstruction safeguards. Browser checks exercise desktop/mobile navigation, actual reveal, coordinated replay, laboratory controls, missing assets and external-request isolation.

Playwright uses installed Microsoft Edge on Windows. On another platform, install the Playwright Chromium browser first with `npx playwright install chromium`. `npm run test:e2e` builds the production bundle, then browser tests start and stop a local static preview server. Test screenshots are under ignored `test-results/`. Test-only intercepted diagnosis fixtures exercise the future export interface; they are never packaged as genuine predictions.

## Seven-minute rehearsal

1. **0:00–0:40** — Overview: explain static research replay, one currently available trained capability, blocked diagnosis, and three illustrations. Do not claim two completed trained components.
2. **0:40–2:10** — Forecasting: inspect demand/solar/wind, reveal actuals, change baseline, inspect calculated net load and value table.
3. **2:10–3:30** — Diagnosis: show the readiness blocker; after genuine exports are supplied, inspect one physical and one sensor episode. Location remains unavailable.
4. **3:30–5:20** — Laboratory: mask telemetry, inspect equipment safeguards, explicitly select a separate hypothetical outage, advance rounds, compare all three actions including no change.
5. **5:20–6:30** — Evaluation: show genuine chronological counts, measured errors, source hash, run origin, measured 76.48-second pipeline and limitations.
6. **6:30–7:00** — Demonstrate an unavailable state, reset to defaults, and state remaining data/research work.

Run twice on the presentation laptop, including once with external networking disconnected. Capture a provenance-visible backup recording after final artifact freeze. Model-owner fixture review and committee-laptop rehearsal are human handoff tasks, not completed validations.
