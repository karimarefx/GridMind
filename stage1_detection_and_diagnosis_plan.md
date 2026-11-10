# GridMind Stage 1: abnormality detection and cause diagnosis

Status: software implemented and tested; first combined experiment completed.
Measured diagnostic effectiveness and independent confirmation remain incomplete.

## Execution record

- Collected 30 ambient records (29 provider/month groups), with source evidence,
  checksums, waveform integrity checks and visual phase review.
- Implemented grouped detector training and complete-pipeline evaluation on 62 records.
- Implemented local upload API, model verification, cleanup, original charts and
  uncertainty-aware interface; packaged the trusted model and measured evaluation.
- Added a short combined-pipeline notebook; executed its code cells successfully.
- Passed 48 Python, 17 frontend unit and 12 desktop/mobile browser tests, plus build.
- Full policy returned only 8/62 decisions, all normal. No physical/timing diagnosis
  was returned in grouped evaluation. The development sensitivity target was not met.
- Independent timing families and deeper normal-label validation remain necessary.
  See `reports/diagnosis/stage1_summary.md`; software availability is experimental.

## Intended behavior

Validate a prepared 60-second, 30 Hz PMU window. Model A decides normal,
abnormal or uncertain. Only abnormal windows enter Model B, which decides
physical disturbance, timing anomaly or uncertain. Invalid inputs are unavailable.
This version handles uploaded windows, not continuous real-time detection.

## Data

| Purpose | Source | Starting status |
| --- | --- | --- |
| Normal | Ambient recordings from PNNL/GESL Providers 9/10 | Must locate, download and verify |
| Physical | Existing GESL Providers 9/10 | 24 curated recordings |
| Timing | Existing GESL data-quality collection | 8 recordings in 3 conservative families |
| Independent confirmation | New source families from compatible collections | Must reserve before inspecting model outcomes |

PNNL documents ambient and disturbance data: https://www.pnnl.gov/publications/open-source-library-phasor-measurement-unit-data-capturing-real-bulk-power-systems
DOE identifies public GESL Providers 9/10: https://www.energy.gov/oe/big-data-synchrophasor-analysis

Aim initially for 30 independently grouped normal recordings across varied conditions.
Verify source descriptions and all five channels. A steady-state equipment tag
alone does not establish normal grid operation or clean sensor measurements.
Do not infer normal labels from absence of event tags or quiet-looking traces.
Ambiguous examples stay excluded with reasons. If normal data cannot be verified,
record the blocker and do not train or substitute synthetic normal data.

## Implementation sequence

1. Curate a normal manifest with source evidence, archive/trace hashes, sample
   bounds, PMU channels and conservative source family IDs.
2. Extend the dataset loader for normal/physical/timing labels while preserving
   the original diagnosis loader and its provenance checks. Use original complete
   measurements with the existing seven-column CSV format and 23 context features.
3. Assign groups before window extraction. Related normal/event intervals share
   their original source family. Use fixed non-overlapping source windows; avoid
   outcome-driven selection. Never use provider or file metadata as features.
4. Train Model A as a 300-tree Random Forest, normal versus abnormal (physical and
   timing combined). Balance class and family weights. Select leaf sizes 1/3/5
   with inner grouped validation. Choose score thresholds using inner predictions
   and report sensitivity, false alarms, normal decisions and uncertainty.
5. Keep Model B's current version and threshold for deployment. For pipeline
   evaluation fit both stages on each outer training partition; do not reuse a
   cause model trained on the outer test families. Use three grouped outer folds
   while the timing class has only three independent groups.
6. Freeze protocols and save both models, feature order, thresholds, dependencies,
   source hashes, group assignments and all measured outcomes. Existing recordings
   remain development data; reserve newly sourced families for final confirmation.
7. Provide a local FastAPI backend with health and multipart CSV diagnosis routes.
   Load only trusted local bundles, validate 1800 original samples, limit files to
   2 MiB, delete temporary files, and serve the built dashboard on loopback port 8000.
   Missing Model A must produce an explicit unavailable detection stage; never
   classify a window as normal or silently bypass detection.
8. Add CSV upload, angle units, input validation, original traces and both-stage
   results to the existing interface. Ground truth for uploads is unknown. Show
   uncertainty and experimental status. Preserve forecasting functionality.
9. Update the explained notebook, setup instructions, model report and exporter;
   exporters must not erase diagnosis readiness or measured evaluation.
10. Test and prepare an isolated GitHub change on codex/stage1-detection-diagnosis.
    Include only relevant code, verified model artifacts and summaries. Keep
    original archives, credentials and uploads outside Git. Do not edit papers.

## Validation and completion

Test source checksums and label evidence, group leakage, feature/unit/reference
invariance, input failures, model round trips, pipeline routing, uncertainty,
API/direct inference equivalence, cleanup, browser uploads and unavailable models.
Run Python tests, frontend tests, production build and browser checks.

Publish detector misses and normal false alarms, cause classification conditioned
on detection, complete-pipeline outcomes and coverage. Development targets are
95% abnormal recall and at most 5% normal false positives; report actual results
and abstention rather than weakening thresholds or inventing success.
Independent validation is a separate completion gate. Software completion alone
does not establish a working abnormality detector.
