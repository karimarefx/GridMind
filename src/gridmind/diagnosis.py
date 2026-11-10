"""Experimental PMU timing-error diagnosis with recording-grouped evaluation.

Only trusted local model bundles may be loaded (joblib uses pickle).
Native GESL downloads must be inspected and normalized before training.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold
from .diagnosis_context import CONTEXT_FEATURES, CONTEXT_VERSION, context_features

VERSION = "pmu-timing-rf-v1"
CLASSES = ["physical", "sensor"]
FEATURES = ["mean_rad", "std_rad", "skew_rad"]
EVENT_VERSION = "pmu-timing-rf-v2"
EVENT_FEATURES = ["median_increment_abs", "increment_rms", "increment_max", "increment_p95",
                  "increment_concentration", "top3_energy_fraction", "increment_mad_ratio",
                  "curvature_rms", "curvature_max", "detrended_std", "detrended_range",
                  "detrended_median_shift", "median_increment_change"]
PROFILES = ["baseline", "event-shape", "measurement-context"]


def profile_spec(profile: str) -> tuple[str, list[str], int]:
    if profile not in PROFILES:
        raise ValueError("Unsupported feature profile")
    return {"baseline": (VERSION, FEATURES, 45), "event-shape": (EVENT_VERSION, EVENT_FEATURES, 90),
            "measurement-context": (CONTEXT_VERSION, CONTEXT_FEATURES, 1800)}[profile]
WINDOW = 45
SEED = 42
SOURCE = "https://doi.org/10.1109/ACCESS.2025.3560602"


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False, suffix=".tmp") as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    temporary.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def event_features(angle: np.ndarray, unit: str) -> np.ndarray:
    """One reference-invariant event vector; an engineering extension, not a paper reproduction."""
    values = np.asarray(angle, dtype=float)
    if values.ndim != 1 or len(values) != 90 or not np.isfinite(values).all():
        raise ValueError("Event-shape profile requires exactly 90 finite phase-angle samples")
    if unit not in {"degree", "radian"}:
        raise ValueError("angle_unit must be degree or radian")
    radians = np.deg2rad(values) if unit == "degree" else values
    radians = np.unwrap(radians - radians[0])
    increment = np.diff(radians)
    slope = np.median(increment)
    centered = increment - slope
    magnitude = np.abs(centered)
    energy = centered ** 2
    curvature = np.diff(increment)
    detrended = radians - np.arange(len(radians)) * slope
    epsilon = 1e-8
    result = np.array([[abs(slope), np.sqrt(np.mean(energy)), magnitude.max(),
                        np.quantile(magnitude, .95), magnitude.max() / (magnitude.sum() + epsilon),
                        np.sort(energy)[-3:].sum() / (energy.sum() + epsilon ** 2),
                        magnitude.max() / (np.median(magnitude) + epsilon),
                        np.sqrt(np.mean(curvature ** 2)), np.max(np.abs(curvature)),
                        detrended.std(ddof=1), np.ptp(detrended),
                        abs(np.median(detrended[-15:]) - np.median(detrended[:15])),
                        abs(np.median(increment[-15:]) - np.median(increment[:15]))]])
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite event-shape features")
    return result


def features(angle: np.ndarray, unit: str, profile: str = "baseline") -> np.ndarray:
    """One row per complete trailing window, preserving the recording boundary.

    Angles are unwrapped before statistics; this explicit implementation choice
    avoids treating +/-180 degree crossings as physical jumps. Constant windows
    have skew zero. No interpolation or imputation is performed.
    """
    if profile == "event-shape":
        return event_features(angle, unit)
    if profile != "baseline":
        raise ValueError("Unsupported feature profile")
    values = np.asarray(angle, dtype=float)
    if values.ndim != 1 or len(values) < WINDOW or not np.isfinite(values).all():
        raise ValueError("Need at least 45 finite phase-angle samples")
    if unit not in {"degree", "radian"}:
        raise ValueError("angle_unit must be degree or radian")
    radians = np.deg2rad(values) if unit == "degree" else values
    radians = np.unwrap(radians)
    windows = np.lib.stride_tricks.sliding_window_view(radians, WINDOW)
    mean = windows.mean(axis=1)
    centered = windows - mean[:, None]
    variance = np.mean(centered ** 2, axis=1)
    skew = np.zeros(len(windows))
    usable = variance > 1e-24
    # Match the adjusted sample skew used by pandas rolling.skew.
    skew[usable] = (np.sqrt(WINDOW * (WINDOW - 1)) / (WINDOW - 2)
                    * np.mean(centered[usable] ** 3, axis=1)
                    / variance[usable] ** 1.5)
    result = np.column_stack([mean, windows.std(axis=1, ddof=1), skew])
    if not np.isfinite(result).all():
        raise ValueError("Feature calculation produced nonfinite values")
    return result


def read_trace(path: Path, unit: str, interval: float, timestamp_precision: float = 0,
               profile: str = "baseline") -> tuple[pd.DataFrame, np.ndarray]:
    """Canonical input is a single original phase-angle channel per CSV."""
    if not np.isfinite(interval) or interval <= 0:
        raise ValueError("sample_interval must be finite and positive")
    if not np.isfinite(timestamp_precision) or not 0 <= timestamp_precision < interval / 10:
        raise ValueError("Timestamp precision must be less than a tenth of the sample interval")
    trace = pd.read_csv(path)
    if not {"elapsed_seconds", "angle", "reconstructed"}.issubset(trace.columns):
        raise ValueError("CSV requires elapsed_seconds, angle, reconstructed")
    time = trace.elapsed_seconds.to_numpy(dtype=float)
    flags = trace.reconstructed.to_numpy(dtype=float)
    if not np.isfinite(time).all() or len(time) < WINDOW:
        raise ValueError("Insufficient or nonfinite timestamps")
    expected = time[0] + np.arange(len(time)) * interval
    if np.any(np.diff(time) <= 0) or np.max(np.abs(time - expected)) > timestamp_precision + 1e-8:
        raise ValueError("Duplicate, unordered, gapped, or unsupported sampling")
    if not np.isfinite(flags).all() or not np.isin(flags, [0, 1]).all():
        raise ValueError("reconstructed must contain only 0 or 1")
    if flags.any():
        raise ValueError("Original-observation baseline rejects reconstructed values")
    matrix = context_features(trace, unit, interval) if profile == "measurement-context" else features(trace.angle.to_numpy(dtype=float), unit, profile)
    return trace, matrix


def load_records(manifest: Path, allow_fixture: bool = False, profile: str = "baseline") -> tuple[list[dict], dict]:
    """Audit all entries, excluding any record without verified provenance."""
    document = json.loads(manifest.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("records"), list):
        raise ValueError("Expected manifest schema_version 1 and records list")
    required = {"record_id", "parent_family_id", "signature_id", "label", "label_verified",
                "label_evidence", "source_url", "origin", "csv", "sha256", "sample_interval",
                "angle_unit", "channel_id", "source_component_id"}
    accepted, rejected, ids, hashes = [], [], set(), set()
    for item in document["records"]:
        record = dict(item)
        try:
            if not required.issubset(record):
                raise ValueError("Missing metadata: " + ", ".join(sorted(required - record.keys())))
            if any(not isinstance(record[key], str) or not record[key].strip()
                   for key in required - {"label_verified", "sample_interval"}):
                raise ValueError("String metadata must be nonempty")
            if record["record_id"] in ids:
                raise ValueError("Duplicate record_id")
            ids.add(record["record_id"])
            if record["label_verified"] is not True or record["label"] not in CLASSES:
                raise ValueError("Label must be verified physical or sensor")
            if record["origin"] != "gesl_field" and not (allow_fixture and record["origin"] == "test_fixture"):
                raise ValueError("Training requires gesl_field source records")
            if record["label"] == "sensor" and "Instrument::Timing" not in record["label_evidence"]:
                raise ValueError("Sensor record requires Instrument::Timing evidence")
            path = (manifest.parent / record["csv"]).resolve()
            if not path.is_relative_to(manifest.parent.resolve()):
                raise ValueError("CSV path must stay inside the manifest directory")
            if sha256(path) != record["sha256"]:
                raise ValueError("CSV checksum mismatch")
            if record["sha256"] in hashes:
                raise ValueError("Duplicate trace content")
            hashes.add(record["sha256"])
            trace, matrix = read_trace(path, record["angle_unit"], record["sample_interval"],
                                       record.get("timestamp_precision", 0), profile)
            record.update(trace=trace, features=matrix, feature_profile=profile)
            accepted.append(record)
        except (ValueError, OSError, TypeError) as error:
            rejected.append({"record_id": record.get("record_id"), "reason": str(error)})
    # A source signature may have many channels/segments, but only one family.
    signature_families = {}
    for record in accepted:
        signature_families.setdefault(record["signature_id"], set()).add(record["parent_family_id"])
    if any(len(groups) != 1 for groups in signature_families.values()):
        raise ValueError("A signature_id appears under different parent families")
    counts = {label: len({r["parent_family_id"] for r in accepted if r["label"] == label})
              for label in CLASSES}
    blockers = []
    if not accepted:
        blockers.append("No verified field recordings imported; obtain authenticated GESL downloads")
    if rejected:
        blockers.append("Resolve rejected manifest entries before training")
    if min(counts.values()) < 3:
        blockers.append("Need at least three independent source families per class")
    audit = {"schema_version": 1, "source_paper": SOURCE, "feature_profile": profile, "manifest_sha256": sha256(manifest),
             "records": len(accepted), "windows": sum(len(r["features"]) for r in accepted),
             "independent_groups_by_class": counts, "rejected": rejected, "blockers": blockers,
             "status": "ready" if accepted and not rejected and min(counts.values()) >= 3 else "blocked",
             "limitation": "Timing-error versus physical disturbance on already abnormal windows only"}
    return accepted, audit


def grouped_splits(records: list[dict], folds: int) -> list[tuple[np.ndarray, np.ndarray]]:
    labels = np.array([r["label"] for r in records])
    groups = np.array([r["parent_family_id"] for r in records])
    unique_groups = np.unique(groups)
    group_labels = []
    for group in unique_groups:
        members = set(labels[groups == group])
        if len(members) != 1:
            raise ValueError("A parent family has conflicting diagnosis labels")
        group_labels.append(next(iter(members)))
    # Stratify independent families rather than window counts. A large family
    # must not prevent a small class from appearing in every held-out fold.
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=SEED)
    splits = [(np.flatnonzero(np.isin(groups, unique_groups[train])),
               np.flatnonzero(np.isin(groups, unique_groups[test])))
              for train, test in splitter.split(unique_groups, group_labels)]
    for train, test in splits:
        if set(groups[train]) & set(groups[test]):
            raise ValueError("Parent family leakage")
        if set(labels[train]) != set(CLASSES) or set(labels[test]) != set(CLASSES):
            raise ValueError("Grouped fold lacks a class; need more independent recordings")
    return splits


def training_weights(records: list[dict]) -> np.ndarray:
    """V2 balances class, family and record using only the training partition."""
    if len({r.get("feature_profile", "baseline") for r in records}) != 1:
        raise ValueError("Cannot mix feature profiles")
    if records[0].get("feature_profile", "baseline") == "baseline":
        return np.concatenate([np.full(len(r["features"]), 1 / len(r["features"])) for r in records])
    families = {c: {r["parent_family_id"] for r in records if r["label"] == c} for c in CLASSES}
    counts = {g: sum(r["parent_family_id"] == g for r in records) for groups in families.values() for g in groups}
    return np.concatenate([np.full(len(r["features"]),
                           1 / (len(families[r["label"]]) * counts[r["parent_family_id"]] * len(r["features"])))
                           for r in records])


def fit(records: list[dict], weight: str | None, leaf: int) -> RandomForestClassifier:
    matrix = np.concatenate([r["features"] for r in records])
    labels = np.concatenate([np.repeat(r["label"], len(r["features"])) for r in records])
    # Equal total weight per record prevents long recordings dominating training.
    weights = training_weights(records)
    model = RandomForestClassifier(n_estimators=300, min_samples_leaf=leaf,
                                   class_weight=weight, random_state=SEED, n_jobs=1)
    model.fit(matrix, labels, sample_weight=weights)
    return model


def probabilities(model: RandomForestClassifier, records: list[dict]) -> np.ndarray:
    order = [list(model.classes_).index(label) for label in CLASSES]
    return np.array([model.predict_proba(r["features"])[:, order].mean(axis=0) for r in records])


def threshold_for(labels: np.ndarray, scores: np.ndarray) -> float:
    predicted = np.array(CLASSES)[scores.argmax(axis=1)]
    maximum = scores.max(axis=1)
    # Lowest threshold gives greatest coverage, requiring predictions for both classes.
    for threshold in np.unique(np.r_[0.5, maximum]):
        kept = maximum >= threshold
        if all(np.any(kept & (predicted == label)) and
               np.mean(labels[kept & (predicted == label)] == label) >= .95
               for label in CLASSES):
            return float(threshold)
    return 1.01  # Explicitly abstain on every sample when precision target is infeasible.


def select_model(records: list[dict]) -> tuple[dict, float]:
    counts = [len({r["parent_family_id"] for r in records if r["label"] == c}) for c in CLASSES]
    folds = min(3, min(counts))
    if folds < 2:
        raise ValueError("Need at least two groups per class for inner validation")
    splits = grouped_splits(records, folds)
    labels = np.array([r["label"] for r in records])
    best_score, best, best_probabilities = -1.0, None, None
    for weight in ([None] if records[0].get("feature_profile", "baseline") != "baseline" else [None, "balanced"]):
        for leaf in [1, 3, 5]:
            scores = np.zeros((len(records), 2))
            for train, validation in splits:
                model = fit([records[i] for i in train], weight, leaf)
                scores[validation] = probabilities(model, [records[i] for i in validation])
            score = f1_score(labels, np.array(CLASSES)[scores.argmax(axis=1)], average="macro")
            if score > best_score:
                best_score = score
                best = {"weight": weight, "leaf": leaf}
                best_probabilities = scores
    return best, threshold_for(labels, best_probabilities)


def metrics(labels: np.ndarray, scores: np.ndarray, decisions: list[str]) -> dict:
    predicted = np.array(CLASSES)[scores.argmax(axis=1)]
    result = classification_report(labels, predicted, labels=CLASSES, output_dict=True, zero_division=0)
    kept = np.array(decisions) != "uncertain"
    selective = {}
    for label in CLASSES:
        selected = kept & (np.array(decisions) == label)
        selective[label] = {"returned": int(selected.sum()),
                            "precision": float(np.mean(labels[selected] == label)) if selected.any() else None}
    return {"classification": result, "selective_by_class": selective,
            "confusion_matrix": confusion_matrix(labels, predicted, labels=CLASSES).tolist(),
            "class_order": CLASSES, "coverage": float(kept.mean()),
            "physical_misrouted_as_sensor": int(np.sum((labels == "physical") & (np.array(decisions) == "sensor"))),
            "selective_accuracy": float(np.mean(labels[kept] == np.array(decisions)[kept])) if kept.any() else None}


def train(manifest: Path, destination: Path, profile: str = "baseline", protocol: Path | None = None) -> None:
    protocol_hash = None
    version, feature_names, window = profile_spec(profile)
    if profile == "baseline" and protocol is not None:
        raise ValueError("A development protocol applies to revised profiles only")
    if profile != "baseline":
        if protocol is None:
            raise ValueError("Revised development requires a frozen --protocol JSON")
        json.loads(protocol.read_text(encoding="utf-8"))
        protocol_hash = sha256(protocol)
    records, audit = load_records(manifest) if profile == "baseline" else load_records(manifest, profile=profile)
    if audit["status"] != "ready":
        raise ValueError("Dataset audit blocks training: " + json.dumps(audit))
    if destination.exists():
        raise ValueError("Use a new output directory to preserve existing model/results")
    intervals = {r["sample_interval"] for r in records}
    if len(intervals) != 1:
        raise ValueError("One model requires one verified sample interval; no automatic resampling")
    minimum = min(audit["independent_groups_by_class"].values())
    splits = grouped_splits(records, 5 if minimum >= 5 else 3)
    labels = np.array([r["label"] for r in records])
    scores, baselines = np.zeros((len(records), 2)), np.empty(len(records), dtype=object)
    decisions, thresholds, fold_ids = ["uncertain"] * len(records), np.ones(len(records)), np.zeros(len(records), int)
    fold_reports, outer_models = [], []
    for fold, (train_indices, test_indices) in enumerate(splits):
        training = [records[i] for i in train_indices]
        test = [records[i] for i in test_indices]
        parameters, threshold = select_model(training)
        model = fit(training, **parameters)
        started = time.perf_counter()
        fold_scores = probabilities(model, test)
        inference_seconds = time.perf_counter() - started
        scores[test_indices] = fold_scores
        dummy = DummyClassifier(strategy="most_frequent").fit(np.zeros((len(training), 1)), labels[train_indices])
        baselines[test_indices] = dummy.predict(np.zeros((len(test), 1)))
        fold_decisions = []
        for index, probability in zip(test_indices, fold_scores):
            decision = CLASSES[int(probability.argmax())] if probability.max() >= threshold else "uncertain"
            decisions[index], thresholds[index], fold_ids[index] = decision, threshold, fold
            fold_decisions.append(decision)
        fold_reports.append({"fold": fold, "parameters": parameters, "threshold": threshold,
                             "prediction_seconds": inference_seconds, "test_records": len(test),
                             "train_groups": sorted({r["parent_family_id"] for r in training}),
                             "test_groups": sorted({r["parent_family_id"] for r in test}),
                             **metrics(labels[test_indices], fold_scores, fold_decisions)})
        outer_models.append({"model": model, "parameters": parameters, "threshold": threshold,
                             "version": f"{version}-outer-{fold}"})
    parameters, threshold = select_model(records)
    final_model = fit(records, **parameters)
    bundle = {"version": version, "model": final_model, "feature_profile": profile,
              "features": feature_names, "window": window,
              "sample_interval": records[0]["sample_interval"], "threshold": threshold,
              "timestamp_precision": max(r.get("timestamp_precision", 0) for r in records),
              "manifest_sha256": audit["manifest_sha256"], "parameters": parameters,
              "protocol_sha256": protocol_hash, "implementation_sha256": sha256(Path(__file__)),
              "context_implementation_sha256": sha256(Path(__file__).with_name("diagnosis_context.py")),
              "sklearn_version": importlib.metadata.version("scikit-learn"),
              "dependencies": {name: importlib.metadata.version(name)
                               for name in ["numpy", "pandas", "scikit-learn", "joblib"]},
              "status": "experimental", "classes": CLASSES,
              "angle_policy": "reference-invariant measurement features" if profile != "baseline" else "convert to radians and unwrap per original recording",
              "scope": "PMU timing anomaly versus physical disturbance; abnormal inputs only"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="diagnosis-", dir=destination.parent))
    try:
        if sha256(manifest) != audit["manifest_sha256"]:
            raise ValueError("Manifest changed during training; discard this run and retry")
        shutil.copyfile(manifest, temporary / "source_manifest.json")
        shutil.copyfile(Path(__file__), temporary / "diagnosis_source.py")
        shutil.copyfile(Path(__file__).with_name("diagnosis_context.py"), temporary / "diagnosis_context_source.py")
        if protocol is not None:
            if sha256(protocol) != protocol_hash:
                raise ValueError("Protocol changed during training")
            shutil.copyfile(protocol, temporary / "protocol.json")
        joblib.dump(bundle, temporary / "model.joblib")
        for outer in outer_models:
            fold_bundle = {**bundle, **outer}
            joblib.dump(fold_bundle, temporary / f"{outer['version']}.joblib")
        restored = joblib.load(temporary / "model.joblib")
        np.testing.assert_array_equal(probabilities(final_model, records), probabilities(restored["model"], records))
        save_json(temporary / "audit.json", audit)
        evaluation = {"status": "experimental", "feature_profile": profile, "model_version": version,
                      "evidence_role": "development; previously examined source families" if profile != "baseline" else "initial pilot",
                      **metrics(labels, scores, decisions),
                      "baseline_macro_f1": float(f1_score(labels, baselines, average="macro")),
                      "folds": fold_reports, "python": platform.python_version(),
                      "audit_manifest_sha256": audit["manifest_sha256"],
                      "protocol_sha256": protocol_hash,
                      "sklearn_version": bundle["sklearn_version"],
                      "limitations": ["Few independent timing-error records", "Uncalibrated scores",
                                      "No normal-operation class or physical-location labels",
                                      "Threshold precision is a validation target, not a guarantee"]}
        save_json(temporary / "evaluation.json", evaluation)
        save_json(temporary / "model_manifest.json", {k: v for k, v in bundle.items() if k != "model"})
        export_heldout(temporary, records, scores, decisions, thresholds, fold_ids, evaluation)
        temporary.rename(destination)
    except Exception:
        shutil.rmtree(temporary)
        raise


def predict(bundle: dict, csv: Path, unit: str, interval: float, episode_id: str) -> dict:
    threshold = bundle["threshold"]
    result = {"prediction_id": episode_id + "-prediction", "episode_id": episode_id,
              "predicted_category": None, "status": "unavailable", "raw_score": None,
              "score_class": "unavailable", "decision_threshold": threshold if threshold <= 1 else None,
              "class_mapping": {"physical": "physical grid disturbance", "sensor": "PMU timing anomaly"},
              "model_version": bundle["version"], "diagnosed_at_utc": datetime.now(timezone.utc).isoformat(),
              "physical_location": None, "reason": None}
    try:
        if not np.isclose(interval, bundle["sample_interval"], rtol=1e-6, atol=1e-9):
            raise ValueError("Unsupported sampling interval")
        trace, matrix = read_trace(csv, unit, interval, bundle.get("timestamp_precision", 0),
                                   bundle.get("feature_profile", "baseline"))
        probability = probabilities(bundle["model"], [{"features": matrix}])[0]
        result.update(raw_score=float(probability.max()), score_class=CLASSES[int(probability.argmax())],
                      observation_window={"start": str(trace.elapsed_seconds.iloc[0]),
                                          "end": str(trace.elapsed_seconds.iloc[-1])},
                      score_kind="uncalibrated", status="uncertain",
                      reason="Score below validated threshold")
        if probability.max() >= bundle["threshold"]:
            result.update(predicted_category=result["score_class"], status="complete", reason=None)
    except (ValueError, OSError, TypeError) as error:
        result["reason"] = str(error)
    return result


def export_heldout(root: Path, records: list[dict], scores: np.ndarray, decisions: list[str],
                   thresholds: np.ndarray, folds: np.ndarray, evaluation: dict) -> None:
    """Stage a separate static diagnosis bundle matching the pushed frontend types.

    Predictions are nested outer-fold results, not final-model training results.
    Source timestamps are represented as elapsed time; no absolute dates invented.
    """
    episodes, predictions, assignments = [], [], []
    output = root / "dashboard" / "diagnosis"
    for index, record in enumerate(records):
        identifier = f"episode-{index:05d}"
        path = f"diagnosis/traces/{identifier}.json"
        trace = record["trace"]
        window = {"start": str(trace.elapsed_seconds.iloc[0]), "end": str(trace.elapsed_seconds.iloc[-1])}
        episodes.append({"episode_id": identifier, "parent_family_id": record["parent_family_id"],
                         "split": "test", "ground_truth_class": record["label"], "input_origin": record["origin"],
                         "trace_path": path, "observation_window": window, "time_basis": "elapsed_seconds",
                         "sample_interval": record["sample_interval"], "sample_count": len(trace),
                         "channel_definitions": [{"channel_id": "phase_angle", "source_component_id": record["source_component_id"],
                                                   "quantity": "phase_angle", "unit": record["angle_unit"]}],
                         "limitations": ["Nested grouped cross-validation prediction", "Anonymized source; location unavailable",
                                         "Sensor category means timing/synchronization anomalies only"]})
        probability = scores[index]
        decision = decisions[index]
        predictions.append({"prediction_id": identifier + "-prediction", "episode_id": identifier,
                            "predicted_category": decision if decision in CLASSES else None,
                            "status": "complete" if decision in CLASSES else "uncertain",
                            "raw_score": float(probability.max()), "score_class": CLASSES[int(probability.argmax())],
                            "decision_threshold": float(thresholds[index]) if thresholds[index] <= 1 else None,
                            "class_mapping": {"physical": "physical grid disturbance", "sensor": "PMU timing anomaly"},
                            "score_kind": "uncalibrated",
                            "model_version": f"{evaluation.get('model_version', VERSION)}-outer-{folds[index]}",
                            "diagnosed_at_utc": datetime.now(timezone.utc).isoformat(), "physical_location": None,
                            "reason": None if decision in CLASSES else "Score below training-only validated threshold",
                            "observation_window": window})
        assignments.append({"record_id": record["record_id"], "signature_id": record["signature_id"],
                            "parent_family_id": record["parent_family_id"], "outer_test_fold": int(folds[index]),
                            "sha256": record["sha256"], "label": record["label"]})
        save_json(root / "dashboard" / path,
                  [{"elapsed_seconds": float(t), "phase_angle": float(v)} for t, v in zip(trace.elapsed_seconds, trace.angle)])
    save_json(output / "event_episodes.json", episodes)
    save_json(output / "diagnosis_predictions.json", predictions)
    save_json(output / "diagnosis_evaluation.json", {
        "status": "available", "class_order": CLASSES,
        "confusion_matrix": evaluation["confusion_matrix"],
        "metrics": {"macro_f1": evaluation["classification"]["macro avg"]["f1-score"],
                    "coverage": evaluation["coverage"], "baseline_macro_f1": evaluation["baseline_macro_f1"]},
        "counts": {"episodes": len(records), "families": len({r["parent_family_id"] for r in records})},
        "limitations": evaluation["limitations"], "evaluation_protocol": "nested recording-grouped cross-validation",
        "confusion_matrix_policy": "Forced binary predictions before abstention; coverage reported separately"})
    save_json(root / "split_manifest.json", assignments)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("manifest", type=Path)
    audit.add_argument("--output", type=Path)
    training = commands.add_parser("train")
    training.add_argument("manifest", type=Path)
    training.add_argument("--output", type=Path, required=True)
    training.add_argument("--profile", choices=PROFILES, default="baseline")
    training.add_argument("--protocol", type=Path, help="Frozen development protocol; required for event-shape")
    evaluation = commands.add_parser("evaluate", help="Read saved nested held-out evaluation")
    evaluation.add_argument("run", type=Path)
    prediction = commands.add_parser("predict")
    prediction.add_argument("model", type=Path, help="Trusted local model.joblib only")
    prediction.add_argument("csv", type=Path)
    prediction.add_argument("--unit", choices=["degree", "radian"], required=True)
    prediction.add_argument("--interval", type=float, required=True)
    prediction.add_argument("--episode-id", required=True)
    prediction.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "train":
        train(args.manifest, args.output, args.profile, args.protocol)
        return
    if args.command == "evaluate":
        print((args.run / "evaluation.json").read_text(encoding="utf-8"))
        return
    if args.command == "audit":
        _, result = load_records(args.manifest)
    else:
        bundle = joblib.load(args.model)
        version = bundle.get("version", "")
        profile = bundle.get("feature_profile", "baseline")
        expected_version, expected_features, _ = profile_spec(profile)
        if profile not in PROFILES or (version != expected_version and not version.startswith(expected_version + "-outer-")) or bundle.get("features") != expected_features:
            raise ValueError("Unsupported model schema")
        if bundle.get("sklearn_version") != importlib.metadata.version("scikit-learn"):
            raise ValueError("Model requires its recorded scikit-learn version")
        result = predict(bundle, args.csv, args.unit, args.interval, args.episode_id)
    if args.output:
        save_json(args.output, result)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
