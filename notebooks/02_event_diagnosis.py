# %% [markdown]
# # GridMind Stage 1: explained cell by cell
#
# **Goal:** given an already abnormal measurement window, distinguish a physical
# grid disturbance from a PMU timing anomaly. This does not detect normal operation,
# diagnose every sensor fault, or locate the faulty equipment.
#
# Flow: **original measurements → input checks → 23 numerical features → Random
# Forest → physical / timing anomaly / uncertain**. Invalid inputs are unavailable.
#
# This tutorial uses the latest `measurement-context` profile. It is an engineering
# extension, not an exact reproduction of a paper. The 32 previously examined
# recordings form a development experiment, not an independent final test.
#
# Open this file in VS Code and use **Run Cell**, or open the matching `.ipynb`.
# Select the Python environment used for this project. If necessary, install from
# the repository root with `python -m pip install -r requirements-diagnosis.txt ipykernel`.
# Authenticated GESL records and the saved model must be available locally; this
# notebook does not sign in, download private data, or contain credentials.
#
# The notebook is delivered without embedded source-measurement outputs. Running
# cells displays your local data. Data preparation and retraining are off by default.

# %% [markdown]
# ## Cell 1 — Import the existing implementation
#
# NumPy performs numerical operations, pandas organizes tables, and joblib reloads
# our trusted local model. The `gridmind` imports are the same functions used by
# the Python pipeline. We reuse them so the tutorial and application stay aligned.

# %%
import json
import sys
import importlib.metadata
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from IPython.display import display

ROOT = next(
    (path for path in [Path.cwd(), *Path.cwd().parents]
     if (path / "src/gridmind/diagnosis.py").is_file()),
    None,
)
if ROOT is None:
    raise RuntimeError("Open the notebook from the GridMind repository or its notebooks folder.")
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gridmind import diagnosis as diagnosis
from gridmind.diagnosis_context import CONTEXT_FEATURES, CONTEXT_VERSION, prepare

print("Repository:", ROOT)
print("Model:", CONTEXT_VERSION)
print("Python:", sys.version.split()[0])

# %% [markdown]
# ## Cell 2 — Set paths and optional actions
#
# A **manifest** lists the recordings, labels, family IDs, source information and
# file checksums. The **run folder** holds a fitted model and its measured evaluation.
#
# Leave both switches false to study the completed experiment without changing it.
# `PREPARE_DATA=True` is only for creating missing 60-second segments from original
# local archives. `RUN_TRAINING=True` creates a new run; it never overwrites the old run.

# %%
PROFILE = "measurement-context"
MANIFEST = ROOT / "data/diagnosis/context/manifest.json"
ORIGINAL_MANIFEST = ROOT / "data/diagnosis/manifest.json"
SOURCE_ARCHIVES = ROOT / "data/diagnosis/source_downloads"
PROTOCOL = ROOT / "reports/diagnosis/v3_protocol.json"
SAVED_RUN = ROOT / "artifacts/diagnosis/gesl-measurement-context-rf-003"
PREPARE_DATA = False
RUN_TRAINING = False

print("Prepare missing data:", PREPARE_DATA)
print("Train a new model:", RUN_TRAINING)

# %% [markdown]
# ## Cell 3 — Prepare 60 seconds of original measurements, if requested
#
# `prepare()` checks the archive checksum and source label, keeps the original PMU
# channel, and extends its previously selected event window to 1,800 original
# samples. At 30 samples/second this covers a 60-second acquisition interval;
# the first-to-last sample separation is approximately 59.967 seconds.
#
# This longer interval can capture jumps recurring every 15–20 seconds. It does
# not interpolate, reconstruct, or independently verify the exact anomaly onset.
# It refuses existing output paths to preserve earlier curation.

# %%
if PREPARE_DATA:
    if MANIFEST.exists():
        raise FileExistsError("Context data already exist; keep PREPARE_DATA=False.")
    prepare(SOURCE_ARCHIVES, ORIGINAL_MANIFEST, MANIFEST)

if not MANIFEST.is_file():
    raise FileNotFoundError(
        "Local context manifest is missing. Obtain the original GESL records and "
        "review manifest, then enable data preparation. See data/diagnosis/README.md."
    )
print("Context manifest is available.")

# %% [markdown]
# ## Cell 4 — Audit recordings and their labels
#
# `load_records()` verifies metadata, source origin, checksums, duplicate content,
# valid labels, timestamps and reconstructed-value flags. It then calculates the
# model features. Rejected entries block training rather than silently disappearing.
#
# `physical` is a source-tagged physical disturbance; `sensor` means a source-tagged
# timing anomaly only. Labels describe recordings, not independently annotated
# fault intervals. Family IDs are conservative grouping assumptions. The eight
# timing recordings represent only three timing families.

# %%
records, audit = diagnosis.load_records(MANIFEST, profile=PROFILE)
if audit["status"] != "ready":
    raise RuntimeError(json.dumps(audit, indent=2))

record_table = pd.DataFrame([
    {"record_id": r["record_id"], "label": r["label"],
     "family": r["parent_family_id"], "samples": len(r["trace"])}
    for r in records
])
display(record_table.groupby("label").agg(recordings=("record_id", "count"),
                                         families=("family", "nunique")))
print("Accepted:", audit["records"], "recordings")

# %% [markdown]
# ## Cell 5 — Inspect one input and validate its format
#
# Each row is one timestamp. The seven columns are elapsed seconds, voltage phase
# angle, reconstruction flag, frequency, voltage magnitude, current magnitude and
# current angle. Both angles use the same declared degree/radian unit; frequency
# is in Hz. Magnitudes retain source scales and are normalized later.
#
# `reconstructed=0` means an original observation. This model rejects reconstructed
# samples, missing values and unsupported timing gaps. Millisecond timestamp
# rounding is allowed within the source's declared precision.

# %%
example = next(r for r in records if r["label"] == "sensor")
example_csv = MANIFEST.parent / example["csv"]
trace, production_features = diagnosis.read_trace(
    example_csv, example["angle_unit"], example["sample_interval"],
    example.get("timestamp_precision", 0), PROFILE,
)
print("Example:", example["record_id"])
print("Source label:", example["label"], "| angle unit:", example["angle_unit"])
print("Samples:", len(trace), "| feature shape:", production_features.shape)
display(trace.head())

# %% [markdown]
# ## Cell 6 — Remove the arbitrary angle reference and calculate phase motion
#
# The next five cells unpack `context_features()` for learning. Cell 11 checks
# that these calculations equal the production function exactly.
#
# Convert degrees to radians if necessary. Subtract the first voltage angle so an
# arbitrary constant reference does not change the result. `unwrap` removes the
# artificial boundary between +180° and −180°.
#
# Phase-derived frequency deviation is `Δphase / (2π × Δtime)`. Subtract its median
# to emphasize transient motion. These calculations describe signal behavior;
# an abrupt change alone does not establish a timing fault.

# %%
interval = example["sample_interval"]
angle = trace.angle.to_numpy(float)
current_angle = trace.current_angle.to_numpy(float)
frequency = trace.frequency.to_numpy(float)
voltage = trace.voltage_magnitude.to_numpy(float)
current = trace.current_magnitude.to_numpy(float)

if example["angle_unit"] == "degree":
    angle, current_angle = np.deg2rad(angle), np.deg2rad(current_angle)

phase = np.unwrap(angle - angle[0])
rate = np.diff(phase) / (2 * np.pi * interval)
residual_rate = rate - np.median(rate)
magnitude = np.abs(residual_rate)
energy = residual_rate ** 2
eps = 1e-8
print("Phase increments:", len(rate))
print("Largest centered phase-derived frequency change:", float(magnitude.max()), "Hz")

# %% [markdown]
# ## Cell 7 — Describe sharp jumps and their recurrence
#
# Candidate impulses exceed the larger of eight median absolute deviations or
# 0.005 Hz. Nearby detections are grouped with a 0.25-second separation rule,
# retaining the larger peak. These fixed engineering thresholds are not learned
# event labels and do not provide a diagnosis by themselves.
#
# The count describes impulses per minute. The interval coefficient of variation
# is standard deviation divided by mean interval: a small value means more regular
# spacing. With fewer than three impulses, that feature is set to zero; zero alone
# does not prove periodic behavior. `eps` prevents division by zero in later ratios.

# %%
mad = np.median(magnitude)
candidates = np.flatnonzero(magnitude > max(8 * mad, .005))
pulses = []
for index in candidates:
    if not pulses or index - pulses[-1] > round(.25 / interval):
        pulses.append(int(index))
    elif magnitude[index] > magnitude[pulses[-1]]:
        pulses[-1] = int(index)

gaps = np.diff(pulses) * interval
gap_cv = gaps.std() / gaps.mean() if len(gaps) >= 2 else 0.
print("Detected impulse candidates:", len(pulses))
print("Inter-impulse intervals, seconds:", gaps.tolist())
print("Interval coefficient of variation:", float(gap_cv))

# %% [markdown]
# ## Cell 8 — Compare phase motion with reported frequency
#
# The PMU supplies a frequency measurement as well as phase angle. Average each
# adjacent frequency pair to align it with a phase increment, remove its median,
# and compare it with the phase-derived deviation. RMS and maximum disagreement
# become two features. They can contain useful evidence but are not a physical
# proof: PMU estimation behavior and timing problems can affect both quantities.

# %%
frequency_step = np.diff(frequency)
reported = (frequency[:-1] + frequency[1:]) / 2
residual = residual_rate - (reported - np.median(reported))
print("RMS disagreement:", float(np.sqrt(np.mean(residual ** 2))), "Hz")
print("Largest disagreement:", float(np.abs(residual).max()), "Hz")

# %% [markdown]
# ## Cell 9 — Describe voltage/current changes around the event
#
# Divide magnitudes by their medians to reduce dependence on their source scale.
# Compare voltage and current angles, and inspect one-second magnitude medians
# before and after the largest phase impulse. Also compare the first and last
# seconds of the full interval.
#
# Physical disturbances and clock errors may affect these signals differently,
# which motivates using them together. The classifier learns an association from
# labeled examples; these features are not deterministic fault rules.

# %%
v = voltage / np.median(voltage)
i = current / max(float(np.median(current)), 1e-8)
relative = np.unwrap(angle - current_angle)
event = int(np.argmax(magnitude)) + 1
event = int(np.clip(event, 30, len(trace) - 31))

def endpoint(x):
    return abs(np.median(x[-30:]) - np.median(x[:30]))

def event_change(x):
    return abs(np.median(x[event:event + 30]) - np.median(x[event - 30:event]))

print("Magnitude comparison centered at sample:", event)
print("Relative voltage change:", float(event_change(v)))
print("Relative current change:", float(event_change(i)))

# %% [markdown]
# ## Cell 10 — Assemble the 23 features
#
# The Random Forest receives these 23 numbers, not all 1,800 raw rows. Features
# summarize sharpness, recurrence, frequency behavior, magnitude changes and
# voltage/current angle differences. Their order is part of the model contract.
# Provider names, IDs, status bits and PMU counts are excluded from the features.

# %%
explained_values = [
    residual_rate.std(), magnitude.max(), np.quantile(magnitude, .99),
    magnitude.max() / (np.sqrt(energy.mean()) + eps),
    np.sort(energy)[-3:].sum() / (energy.sum() + eps ** 2),
    len(pulses) * 60 / (len(trace) * interval), gap_cv,
    np.ptp(frequency), np.abs(frequency_step).max(),
    np.abs(frequency_step).max() / (np.sqrt(np.mean(frequency_step ** 2)) + eps),
    endpoint(frequency), np.sqrt(np.mean(residual ** 2)), np.abs(residual).max(),
    np.ptp(v), np.abs(np.diff(v)).max(), endpoint(v),
    np.ptp(i), np.abs(np.diff(i)).max(), endpoint(i),
    np.ptp(relative), np.abs(np.diff(relative)).max(), event_change(v), event_change(i),
]
explained_features = np.asarray([explained_values])
display(pd.DataFrame({"feature": CONTEXT_FEATURES, "value": explained_features[0]}))

# %% [markdown]
# ## Cell 11 — Check the explanation against the actual implementation
#
# This assertion catches a mismatch between the teaching cells and production
# code. It is a software consistency check, not evidence of classification accuracy.
# The application uses `context_features()` through `read_trace()`.

# %%
np.testing.assert_allclose(explained_features, production_features, rtol=0, atol=1e-12)
print("All 23 explained features match the production feature vector.")

# %% [markdown]
# ## Cell 12 — Build the training table and balance its weights
#
# Here `X` has one row per recording and 23 columns; `y` holds physical/sensor labels.
# Related recordings share a family. More recordings from one family do not make
# that family independent evidence multiple times.
#
# The training code assigns equal total weight to each class, then divides that
# weight equally among its families and the recordings within each family. During
# evaluation these weights are calculated using the training partition only.
# The table below illustrates the rule on the full development sample.

# %%
X = np.concatenate([r["features"] for r in records])
y = np.array([r["label"] for r in records])
groups = np.array([r["parent_family_id"] for r in records])
weights = diagnosis.training_weights(records)
print("X shape:", X.shape, "| y shape:", y.shape)
weight_table = pd.DataFrame({"label": y, "family": groups, "weight": weights})
display(weight_table.groupby("label").weight.sum().rename("total class weight"))
display(weight_table.groupby(["label", "family"]).weight.sum().rename("family weight"))

# %% [markdown]
# ## Cell 13 — Keep related families out of the same training/test split
#
# A random row split could put related events into both training and testing,
# making the model appear stronger than it is. `grouped_splits()` keeps each family
# entirely on one side. Three outer folds let every recording be tested once.
#
# Inside each outer training set, separate inner family folds choose the tree-leaf
# setting and abstention threshold. The outer test family is not used for those
# choices. However, these same data informed successive model designs, so the
# overall experiment remains development work, not a new independent final test.

# %%
splits = diagnosis.grouped_splits(records, 3)
split_rows = []
for fold, (training, testing) in enumerate(splits):
    assert not set(groups[training]) & set(groups[testing])
    split_rows.append({
        "fold": fold, "training_records": len(training), "test_records": len(testing),
        "training_families": len(set(groups[training])),
        "test_families": len(set(groups[testing])),
        "test_timing_records": int(np.sum(y[testing] == "sensor")),
    })
display(pd.DataFrame(split_rows))

# %% [markdown]
# ## Cell 14 — Train and save a new run, only if explicitly enabled
#
# `train()` calls the existing training functions:
#
# 1. `select_model()` tests `min_samples_leaf` values 1, 3 and 5 in inner family
#    folds, choosing the largest macro F1. Macro F1 weights both classes equally.
# 2. `fit()` trains 300 Random Forest trees with seed 42 and the family/class weights.
# 3. `threshold_for()` seeks a maximum-score cutoff with at least 95% observed
#    precision for each returned class in inner validation. If none exists, an
#    internal cutoff of 1.01 makes that model abstain on every prediction.
# 4. Outer models produce evaluation predictions. A final model is fitted using
#    all recordings for later inference. The run saves models, evaluation, feature
#    order, versions, protocol, source hashes and family splits.
#
# Scores are uncalibrated. A 0.95 validation precision target is not a guarantee
# of 95% performance on new data. The two timing misses are not fixed by rerunning.

# %%
if RUN_TRAINING:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    ACTIVE_RUN = ROOT / "artifacts/diagnosis" / f"notebook-context-{timestamp}"
    diagnosis.train(MANIFEST, ACTIVE_RUN, profile=PROFILE, protocol=PROTOCOL)
    print("New run saved:", ACTIVE_RUN)
else:
    ACTIVE_RUN = SAVED_RUN
    print("Using the existing run; no retraining:", ACTIVE_RUN)

if not (ACTIVE_RUN / "evaluation.json").is_file():
    raise FileNotFoundError("The saved run is missing. Restore it or explicitly enable training.")

# %% [markdown]
# ## Cell 15 — Read actual evaluation results
#
# **Forced classification** always takes the class with the larger score, ignoring
# abstention. **Returned diagnoses** apply each outer model's validation cutoff.
# Coverage is the fraction receiving a diagnosis. Accuracy among returned
# diagnoses must always be reported beside coverage.
#
# For the saved v3 run: forced predictions detect 6/8 timing events and classify
# 24/24 physical events correctly. After abstention only 11/32 receive diagnoses
# (all 11 correct in this sample), while 21 are uncertain. These are not results
# from the final model predicting its own training data.

# %%
evaluation = json.loads((ACTIVE_RUN / "evaluation.json").read_text(encoding="utf-8"))
if evaluation["audit_manifest_sha256"] != diagnosis.sha256(MANIFEST):
    raise RuntimeError("Saved evaluation belongs to a different data manifest.")

returned = sum(item["returned"] for item in evaluation["selective_by_class"].values())
display(pd.DataFrame([
    {"measure": "Forced accuracy", "value": evaluation["classification"]["accuracy"]},
    {"measure": "Timing recall, forced", "value": evaluation["classification"]["sensor"]["recall"]},
    {"measure": "Physical recall, forced", "value": evaluation["classification"]["physical"]["recall"]},
    {"measure": "Macro F1, forced", "value": evaluation["classification"]["macro avg"]["f1-score"]},
    {"measure": "Majority baseline macro F1", "value": evaluation["baseline_macro_f1"]},
    {"measure": "Coverage after abstention", "value": evaluation["coverage"]},
    {"measure": "Accuracy among returned diagnoses", "value": evaluation["selective_accuracy"]},
]))
print("Diagnoses returned:", returned, "| uncertain:", len(records) - returned)
display(pd.DataFrame(evaluation["confusion_matrix"],
                     index=["actual physical", "actual timing"],
                     columns=["predicted physical", "predicted timing"]))

# %% [markdown]
# ## Cell 16 — Inspect the three outer folds
#
# Different outer folds contain different timing families. Some inner training
# sets could not establish a usable precision cutoff, so those outer models
# abstained on all their test records. In the saved run only fold 2 returned
# diagnoses. Overall counts must not conceal this uneven family coverage.
# A missing displayed cutoff below means the internal value exceeded 1.

# %%
display(pd.DataFrame([
    {"fold": fold["fold"], "test_records": fold["test_records"],
     "min_samples_leaf": fold["parameters"]["leaf"],
     "usable_cutoff": fold["threshold"] if fold["threshold"] <= 1 else None,
     "coverage": fold["coverage"],
     "forced_timing_recall": fold["classification"]["sensor"]["recall"]}
    for fold in evaluation["folds"]
]))

# %% [markdown]
# ## Cell 17 — Load the trusted final model and run one prediction
#
# Only load our own local `model.joblib`; model files are executable Python
# serialization, not ordinary CSV input. Check the recorded scikit-learn version,
# feature profile and ordered feature list against this implementation.
#
# `predict()` validates the CSV, computes the same 23 features, obtains class scores
# and applies the saved cutoff. It returns physical, sensor (timing), uncertain or
# unavailable. Location remains null. This demonstration uses a recording seen by
# the final model during fitting; its answer is not an independent accuracy test.

# %%
model_metadata = json.loads((ACTIVE_RUN / "model_manifest.json").read_text(encoding="utf-8"))
if model_metadata["sklearn_version"] != importlib.metadata.version("scikit-learn"):
    raise RuntimeError("Use the scikit-learn version recorded in the model manifest.")
assert model_metadata["feature_profile"] == PROFILE
assert model_metadata["features"] == CONTEXT_FEATURES
assert model_metadata["version"] == CONTEXT_VERSION
bundle = joblib.load(ACTIVE_RUN / "model.joblib")
assert bundle["features"] == CONTEXT_FEATURES
prediction = diagnosis.predict(
    bundle, example_csv, example["angle_unit"], interval, example["record_id"],
)
display(pd.Series(prediction, name="final-model demonstration"))

# %% [markdown]
# ## Cell 18 — Compare with the model that had not trained on this family
#
# Find this recording's outer test fold and load that fold's model. It was trained
# without this event family. Its scores and abstention policy are the source of
# the saved grouped evaluation, unlike the final-model demonstration above.
# Results may differ because the training data and thresholds differ.

# %%
assignments = json.loads((ACTIVE_RUN / "split_manifest.json").read_text(encoding="utf-8"))
assignment = next(row for row in assignments if row["record_id"] == example["record_id"])
fold = assignment["outer_test_fold"]
outer_bundle = joblib.load(ACTIVE_RUN / f"{CONTEXT_VERSION}-outer-{fold}.joblib")
fold_report = next(row for row in evaluation["folds"] if row["fold"] == fold)
assert example["parent_family_id"] not in fold_report["train_groups"]
outer_prediction = diagnosis.predict(
    outer_bundle, example_csv, example["angle_unit"], interval, example["record_id"],
)
display(pd.DataFrame([
    {"model": "final; trained on all records", "status": prediction["status"],
     "category": prediction["predicted_category"], "score_class": prediction["score_class"],
     "raw_score": prediction["raw_score"]},
    {"model": "outer fold; this family excluded", "status": outer_prediction["status"],
     "category": outer_prediction["predicted_category"], "score_class": outer_prediction["score_class"],
     "raw_score": outer_prediction["raw_score"]},
]))

# %% [markdown]
# ## Cell 19 — Try a different prepared CSV, optionally
#
# Set `CUSTOM_CSV` to a local prepared file. It must contain the seven columns and
# 1,800 original 30 Hz samples, with both angle columns in `CUSTOM_ANGLE_UNIT`.
# Arbitrary uploads have no supplied ground truth, so a returned diagnosis must
# not be described as correct merely because the code returned it.
# This cell does not modify the model, papers or frontend.

# %%
CUSTOM_CSV = None  # Example: Path(r"D:\my_measurements\prepared_window.csv")
CUSTOM_ANGLE_UNIT = "degree"
if CUSTOM_CSV is not None:
    custom_prediction = diagnosis.predict(
        bundle, Path(CUSTOM_CSV), CUSTOM_ANGLE_UNIT, 1 / 30, "custom-window",
    )
    display(pd.Series(custom_prediction, name="uploaded input; ground truth not supplied"))
else:
    print("Optional custom prediction skipped; set CUSTOM_CSV to use your own input.")

# %% [markdown]
# ## Cell 20 — Understand what will connect to the interface
#
# **Training/research:** the preceding steps prepare data, build features, fit the
# model and measure grouped performance. The interface must not retrain on upload.
#
# **Live upload:** the planned Python service loads the trusted final model once,
# then calls `diagnosis.predict()` for a compatible user CSV. The browser displays
# the returned category, score, uncertainty and original measurements. The backend
# and upload interface have not been implemented by this tutorial.
#
# **Saved replay:** the run also contains JSON exports produced by outer-fold
# models. Those exports are different from a live final-model prediction. The
# following cell lists prepared files only; it does not install them in the PoC.
#
# The remaining research limit is generalization: two Eastern periodic timing
# recordings were missed in forced classification. Only three timing families
# exist in this sample. New independent families and better interval/channel
# annotations are required before claiming reliable real-world performance.

# %%
for filename in ["event_episodes.json", "diagnosis_predictions.json", "diagnosis_evaluation.json"]:
    path = ACTIVE_RUN / "dashboard/diagnosis" / filename
    print(filename, "— available" if path.is_file() else "— missing")
print("Detailed results:", ROOT / "reports/diagnosis/repair_summary.md")
