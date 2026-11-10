# Stage 1 source data

The initial task is PMU timing/synchronization anomaly versus physical disturbance,
given an already abnormal window. Its reference is Biswas et al.,
[IEEE Access 2025](https://doi.org/10.1109/ACCESS.2025.3560602).

## Access and import

The [GESL dashboard](https://gsl.ornl.gov/dashboard) requires an account login.
Authenticated downloads were obtained on 8 November 2026. The first curated sample
contains 24 physical-event and 8 timing-error windows from 38 downloaded archives.
Conservative grouping gives 20 physical-event families and only 3 timing-error
families. The latter count is too small for a deployment claim. The source data are
stored locally under ignored `source_downloads/` and `records/` directories.

`review.json` records source metadata, archive hashes, selected phase-angle channels,
90-sample segment bounds, review decisions and grouping assumptions. `import_report.json`
records six exclusions for mixed labels, gaps, or 60 Hz cadence. Both classes use
the same largest-circular-phase-step candidate selection, followed by trace review.
The label is inherited from a source-tagged recording. No independent per-window
ground-truth annotation was supplied. This is an offline event-centered benchmark.

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m gridmind.gesl inspect data/diagnosis/source_downloads --output data/diagnosis/new-review.json
# Inspect candidates and traces, then supply reviewed decisions and source-family IDs.
python -m gridmind.gesl prepare data/diagnosis/source_downloads data/diagnosis/review.json --output data/diagnosis/manifest.json
```

The observed data exports use `_vp_a` or `.vp_a` for positive-sequence voltage
angle, expressed in degrees. The importer normalizes the column separator, retaining
the original measurements. Source timestamps are rounded to milliseconds. Their
declared `timestamp_precision` permits bounded rounding residuals against the exact
30 Hz cadence, without replacing timestamps or allowing dropped samples.

Download original signatures through the supported dashboard. Inspect the actual
download schema before converting it. Retain the source files separately. For each
PMU phase-angle channel, write a CSV with these columns.

| Column | Meaning |
| --- | --- |
| elapsed_seconds | Actual source time relative to the recording's first sample |
| angle | Original measured phase angle |
| reconstructed | 0 for original, 1 for reconstructed; this baseline requires all 0 |

Declare the unit as `degree` or `radian`. Preserve the source cadence and wrap
convention. Convert timestamps to elapsed seconds without changing their spacing.
Do not interpolate or resample. Segment bounds and selection policy must be recorded
in the review manifest. The baseline rejects missing
or reconstructed samples, so those records remain explicitly excluded in the audit.

Add each inspected channel/segment to `manifest.json`. The following is a metadata
example, not a supplied field recording.

```json
{
  "schema_version": 1,
  "records": [{
    "record_id": "gesl-signature-channel-segment",
    "parent_family_id": "original-event-family",
    "signature_id": "source-signature-id",
    "label": "sensor",
    "label_verified": true,
    "label_evidence": "Instrument::Timing; inspected source annotation and segment bounds",
    "source_url": "https://gsl.ornl.gov/",
    "origin": "gesl_field",
    "csv": "records/inspected-channel.csv",
    "sha256": "replace-with-the-normalized-csv-sha256",
    "sample_interval": 0.03333333333333333,
    "angle_unit": "degree",
    "channel_id": "source-phase-angle-channel",
    "source_component_id": "source-anonymized-pmu-id"
  }]
}
```

Use label `physical` only for a source-confirmed physical disturbance. Sensor labels
initially require `Instrument::Timing`. Group all channels, segments and variants of
the same original event under one `parent_family_id`. Different signatures from the
same original event must also share that family. Never invent bus mappings.

The loader validates the schema, checksum, duplicate content, cadence, units, labels
and reconstructed flags. The metadata is a curator assertion, so source annotation
review is still required. It cannot infer independent-event identity from waveforms.

## Run

The latest experimental profile is `measurement-context`. It needs a complete
60-second, 30 Hz segment with the same PMU's original voltage phase angle,
frequency, voltage magnitude, current magnitude and current angle. No additional
download is needed to reproduce the existing local sample. It retains the original
32 source recordings and families, and extends their source segment bounds.
The normalized context data are local and ignored under `context/records/`.

```powershell
$env:PYTHONPATH = "$PWD\src"
# Preparation refuses to overwrite an existing context manifest or trace.
python -m gridmind.diagnosis_context data/diagnosis/source_downloads data/diagnosis/manifest.json --output data/diagnosis/context/manifest.json
# Use a fresh run directory; the completed run is gesl-measurement-context-rf-003.
python -m gridmind.diagnosis train data/diagnosis/context/manifest.json --profile measurement-context --protocol reports/diagnosis/v3_protocol.json --output artifacts/diagnosis/new-context-run
python -m gridmind.diagnosis evaluate artifacts/diagnosis/gesl-measurement-context-rf-003
python -m gridmind.diagnosis predict artifacts/diagnosis/gesl-measurement-context-rf-003/model.joblib data/diagnosis/context/records/gesl-5711-P029_vp_a-context.csv --unit degree --interval 0.03333333333333333 --episode-id timing-example
```

This is a development comparison on previously examined families. The model is
not installed in the live frontend. See [current results](../../reports/diagnosis/repair_summary.md).
The commands below preserve the original short-angle baseline for comparison.

From the repository root in PowerShell, using Python 3.11 or newer.

```powershell
python -m pip install -r requirements-diagnosis.txt
$env:PYTHONPATH = "$PWD\src"
python -m gridmind.diagnosis audit data/diagnosis/manifest.json --output reports/diagnosis/audit.json
python -m gridmind.diagnosis train data/diagnosis/manifest.json --output artifacts/diagnosis/run-001
python -m gridmind.diagnosis evaluate artifacts/diagnosis/run-001
python -m gridmind.diagnosis predict artifacts/diagnosis/run-001/model.joblib data/diagnosis/records/inspected-channel.csv --unit degree --interval 0.03333333333333333 --episode-id inspected-001
python -m pytest tests/test_diagnosis.py -q
```

Training requires at least three independent groups per class, compatible cadence,
and no rejected manifest entries. Families with conflicting labels are rejected.
Five outer folds are used with at least five
groups per class, otherwise three. If grouped stratification produces a fold without
both classes, training stops. Every outer test prediction uses a model and threshold
selected only within that fold's training records. Inner validation tests unweighted
and balanced Random Forests, with 300 trees and minimum leaf sizes 1, 3, and 5.

Features are rolling sample mean, sample standard deviation, and adjusted sample skew
over 45 samples. Angles are converted to radians and unwrapped per source recording.
Scores are averaged over all windows of a record. Equal total training weight per
record prevents long traces dominating. These are documented adaptations of the
paper; the current implementation is not a numerical reproduction of its results.

An abstention threshold targets 95% precision for both returned classes on inner
validation. An infeasible threshold abstains on every sample. This target is not an
accuracy guarantee. Missing values, reconstructed readings, timing gaps and unknown
sampling intervals return unavailable. The caller must supply abnormal windows.

## Saved outputs and existing interface

Each new run directory contains the final model, outer-fold models, input/schema manifest, audit,
nested cross-validation metrics, parent-family fold assignments and a `dashboard/`
directory containing the existing episode/prediction/evaluation JSON contracts.
The confusion matrix uses forced binary decisions before abstention. Coverage and
physical-to-sensor routing failures are reported separately.

`dashboard/diagnosis/` is a staging export, not a replacement for the frontend's
complete data bundle. Its records are genuine held-out predictions only after a
field-data run. Fold model versions distinguish them from the all-records final
model. Only publish field-data exports with their experimental limitations visible.
To publish a complete compatible bundle, include these staged assets and update the
catalog/run metadata and bundle checksums using the existing frontend handoff rules.
Do not run the forecasting export script over a new bundle.

Load only trusted local joblib files. Persisted models require the recorded
scikit-learn version. GESL has anonymized topology, so these records alone do not
support a Stage 2 localization claim. Also, clock-error classification does not
establish performance for sensor drift, frozen sensors, cyberattacks or mixed events.
