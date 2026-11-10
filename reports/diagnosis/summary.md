# Stage 1 GESL pilot

The data access and training pipeline work. This first classifier does **not** meet
the physical-versus-timing-error diagnosis objective and must remain experimental.
No diagnosis model was installed in the live frontend.

## Data

Authenticated GESL downloads were obtained on 8 November 2026. Of 38 source archives,
32 recordings supplied one 90-sample, 30 Hz phase-angle segment each: 24 physical
disturbances and 8 timing errors. Six archives were excluded for gaps or timing
irregularities, mixed physical/timing labels, or incompatible 60 Hz cadence.
The timing examples were conservatively assigned to only three families; physical
examples were grouped by provider and event month into 20 families. These are
curation assumptions, not independently established event identities.

Both classes used the largest circular phase-step candidate selection followed by
trace review. Labels come from source recording tags; the selected segments do not
have independent per-window annotations. This convenience sample is an offline,
event-centered pilot, not an evaluation of continuous abnormal-event detection.
Original angles and rounded timestamps were retained without reconstruction or
resampling. Source archives and normalized measurements remain in ignored local
directories; the review and manifest record checksums and selection decisions.

## Measured results

Three outer family-grouped folds were used. Hyperparameters and abstention
thresholds were selected using inner grouped folds, without their outer test data.
Each 90-sample segment produced 46 trailing 45-sample feature windows; metrics
below are at recording level after averaging their probabilities.

| Measure | Result |
| --- | --- |
| Forced binary accuracy | 62.5% (20/32) |
| Physical recall | 83.3% (20/24) |
| Timing-error recall | 0% (0/8) |
| Macro F1 | 0.385 |
| Majority-class baseline macro F1 | 0.429 |
| Coverage after abstention | 0% (all 32 uncertain) |

The forced binary confusion matrix is `[[20, 4], [8, 0]]`, with physical then
sensor as both row and column order. The classifier underperformed the majority
baseline. No inner-fold threshold met the required precision for both returned
classes, so abstention disabled confident classification. Zero returned errors
under that policy is not evidence of useful diagnosis: it returned no diagnoses.

## Artifacts and limits

The saved run is `artifacts/diagnosis/gesl-timing-rf-001/`: model bundles, dependency
manifest, source-manifest snapshot, grouped split assignments, evaluation, and
staged dashboard exports. `evaluation.json` beside this report is a copy of the
measured run evaluation. Inference uses an uncalibrated Random Forest score.
All 22 Python tests passed after implementation, including import and data checks.
Tests verify software behavior; they do not establish model effectiveness.

Before another effectiveness claim, obtain more independent timing-event families
and better evidence that selected segments contain the tagged timing anomaly.
Review source family relationships and define a new evaluation protocol before
the next experiment. Preserve this failed pilot; repeated tuning against these
same outer results would not create an independent final test.

Research papers and paper-selection sheets were not edited.
