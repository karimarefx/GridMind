# Stage 1 repair: measured development results

The original all-missed timing-error result has improved substantially, but the
diagnosis model is still experimental. The current candidate detects six of eight
timing examples in forced classification. It does not justify a general sensor
fault classifier or deployment claim.

## What changed and why

The original model used absolute phase-angle mean and averaged predictions from
46 overlapping windows in a three-second segment. A reference-angle audit changed
the original model's forced prediction for 4/32 records solely by applying constant
phase rotations. That establishes an unwanted reference dependency; it does not
establish that this was the sole cause of the missed timing events.

The first repair replaced the original statistics with 13 reference-invariant
event-shape features and balanced the training weight by class, family and record.
It detected only 1/8 timing examples. This failed intermediate result is retained.

The current measurement-context candidate uses one original 60-second segment
around each unchanged pilot phase candidate, keeping the same 32 source records,
channel choices, source labels, family assignments and outer folds. This covers
more of the 15–20 second recurrence described in several source timing annotations.
It adds reported frequency, voltage/current magnitudes and current angle to phase
angle. Its 23 fixed features describe phase impulses and recurrence, phase/frequency
agreement, relative magnitude changes and voltage/current angle differences.
Provider, source ID, PMU count, status bits and metadata are not model features.
No measurements were reconstructed or resampled. This is an engineering extension
of the project baseline, not an exact reproduction of a research paper.

## Results

Each experiment used three outer family-grouped folds and inner grouped model
selection. The precision target for returned diagnoses remained 95% for each
returned class. Class and family weighting use only the training partition.

| Candidate | Timing detected, forced | Physical correct, forced | Macro F1 | Returned diagnoses |
| --- | --- | --- | --- | --- |
| Original three statistics | 0/8 | 20/24 | 0.385 | 0/32 |
| Three-second event shape | 1/8 | 24/24 | 0.547 | 0/32 |
| 60-second measurement context | 6/8 | 24/24 | 0.909 | 11/32 |

The current forced accuracy is 30/32 (93.75%), with confusion matrix
`[[24, 0], [2, 6]]` in physical/sensor order. After abstention it returned six
physical and five timing diagnoses, all correct in this development sample;
21 records were uncertain. That is 34.375% coverage, not 100% effective accuracy.
Both forced timing misses belong to the Eastern periodic-clock family. Timing
detection therefore succeeded in two of three timing families. Outer folds 0 and
1 returned no diagnoses because their inner validation could not meet the
classwise precision policy; fold 2 returned all 11 of its diagnoses.

These data and prior outcomes had already been inspected. Each revised candidate
had a protocol recorded before its evaluation, but those protocols do not turn
reused data into an independent final test. The numbers above are development
comparisons and must not be described as externally validated performance.

## How it runs

Input is an **already abnormal**, complete 60-second, 30 Hz interval with phase
angle, frequency, voltage magnitude, current magnitude and current angle from the
same PMU. It produces physical, timing anomaly, uncertain, or unavailable for an
invalid input. It requires the longer interval; the original short single-angle
input cannot substitute for these measurements. Current and voltage angles must
use the declared common degree/radian unit and a consistent reference.

The source preparation module is `src/gridmind/diagnosis_context.py`. The profile
in `src/gridmind/diagnosis.py` is `measurement-context`. The saved trusted local
bundle is `artifacts/diagnosis/gesl-measurement-context-rf-003/model.joblib`.
That run includes source-code snapshots, hashes, protocol, dependency versions,
source manifest, splits, evaluation and staged dashboard exports. It was not
installed in the live frontend. Its final model's validation threshold is not an
independent performance guarantee.

## Verification and remaining limits

All 33 Python tests pass. Checks cover reference-angle and unit invariance, event
representation, recurrence, balanced family weighting, grouped splits, invalid
measurements, model persistence and legacy model compatibility. Separately, all
32 context records were verified against their archived source measurements,
their outer family assignments were checked against the original pilot, and
their saved outer-model scores were unchanged under 90/180/270-degree reference
rotations. See `repair_comparison.json` for per-record outcomes.

The remaining issue is generalization to independent clock-error families. Three
timing families are a small basis, and labels still describe recordings rather
than independently annotated affected intervals/channels. Physical and timing
archives come from different provider collections, so measurement artifacts may
remain confounded with class even without explicit provider features. There is
no normal class, location output, or coverage of other sensor fault types.

The next effectiveness test must use new source families and independently checked
anomaly intervals/channels, with this candidate fixed before examining their
outcomes. More tuning on these 32 examples cannot substitute for that test.
The original and intermediate failed runs are preserved. Papers and paper-selection
sheets were not edited.
