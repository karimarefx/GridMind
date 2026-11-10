# Complete Stage 1 pilot: detection followed by cause classification

The local upload software is implemented. The measured combined model is
experimental and does not yet meet the research goal of useful end-to-end diagnosis.

## Data and provenance

The pilot contains 62 original one-minute windows: 30 source-labeled ambient,
24 physical and eight timing examples, grouped into 41 conservative families.
The 30 ambient recordings represent 29 provider/month groups (one month has two
recordings). Normal and physical examples sharing a provider/month stay together.
The timing examples still represent only three families. No independent final
timing-family test is available.

Ambient candidates were downloaded through the authenticated GESL dashboard from
Providers 9/10 on 10 November 2026, selecting exclusive nonspecific steady-state
tags and one-minute records across dates. The first complete lexicographic PMU
was selected, without looking for the quietest trace. All channels pass numerical
integrity checks; selected voltage phase plots were visually inspected and show
smooth ambient evolution. This does not independently prove that all sensors
were healthy. Source tags are the label evidence. The Western metadata declares
60 Hz, but actual timestamps and row counts show original 30 Hz; timestamps were
validated without resampling. UI/source metadata date/time inconsistencies are
not used as model features.

Raw archives and normalized CSVs remain in ignored local folders. Local
`data/diagnosis/stage1/normal_review.json` records metadata and selection decisions.
The cause data retain the prior event-centered channel selection; this difference
in normal/abnormal selection is a potential confound.

## Fixed protocol and results

The detector uses the unchanged 23 context features and a 300-tree Random Forest.
Inner family folds select leaf size and two classwise precision cutoffs; uncertain
inputs are not silently routed into diagnosis. Outer cause models are fitted
without any outer test family. Three outer folds report the complete pipeline.
The source protocol was frozen before evaluation. Previously examined abnormal
records remain development data.

| Measure | Measured result |
| --- | --- |
| Forced detector normal correct | 30/30 |
| Forced detector abnormal correct | 30/32 |
| Forced detector accuracy | 60/62 (96.77%) |
| Detector abnormal recall after uncertainty | 10/32 (31.25%) |
| Normal false alarms after uncertainty | 0/30 |
| Detector uncertain inputs | 44/62 |
| Complete-pipeline returned decisions | 8/62 (12.90%) |
| Complete-pipeline uncertain inputs | 54/62 |
| Returned normal decisions | 8, all correct in this sample |
| Returned physical/timing diagnoses | 0 |

The detector's forced matrix is `[[30, 0], [2, 30]]`, with normal/abnormal order.
After the complete confidence policy, the pipeline matrix has actual rows normal,
physical, timing and predicted columns normal, physical, timing, uncertain:

```
[[8, 0, 0, 22],
 [0, 0, 0, 24],
 [0, 0, 0,  8]]
```

All eight returned decisions being correct does not establish a reliable
diagnostic system: no abnormal cause diagnosis was returned. The 95% precision
validation targets cannot be supported consistently by the small inner samples.
The declared 95% abnormal-recall development target was not achieved after
abstention. Preserve this result; do not relax the policy against outer outcomes
and present that as independent validation.

## Software and use

`models/stage1/` contains the trusted combined model, checksum/dependency manifest,
protocol and evaluation. The final cause model is the frozen v3 bundle; the final
detector is fitted on all development records. Uploaded predictions therefore
use a different fitted model from the outer-fold evaluation models.

The local FastAPI service validates a prepared CSV, calculates features, applies
detection, then runs cause classification only for confidently abnormal inputs.
It returns normal, physical, timing, uncertain, or an input error. It never assumes
ground truth for uploads. It serves the built frontend on loopback port 8000;
uploads are processed in bounded temporary storage and removed after requests.
The UI displays original values, uncalibrated scores, both decisions and measured
pipeline coverage. Missing models are explicit unavailable states.

Validation completed: 48 Python tests; 17 frontend unit tests; 12 desktop/mobile
browser tests; TypeScript/production build. Browser tests call the real local
Python API with explicitly synthetic software fixtures, not accuracy examples.

## Remaining research work

Obtain independent timing families and better affected-channel/interval labels;
validate ambient examples more deeply; use a common window/channel selection
policy across classes in a new frozen study. Confirm performance on untouched
sources before claiming operational abnormality detection or cause diagnosis.
Continuous monitoring, detection-delay measurement, localization and other sensor
fault types are outside this upload prototype. Papers and paper-selection sheets
were not changed.
