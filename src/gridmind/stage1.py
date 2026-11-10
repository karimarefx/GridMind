"""Experimental normal/abnormal detector followed by PMU cause classification."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import shutil
import tempfile

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold

from . import diagnosis as d
from .diagnosis_context import CONTEXT_FEATURES
from .normal_data import NORMAL_TAG

VERSION = "gridmind-stage1-v1"
DETECTION_CLASSES = ["normal", "abnormal"]
OUTPUT_CLASSES = ["normal", "physical", "sensor", "uncertain"]


def load_data(normal_manifest: Path, cause_manifest: Path, allow_fixture=False):
    abnormal, audit = d.load_records(cause_manifest, allow_fixture=allow_fixture, profile="measurement-context")
    if audit["status"] != "ready":
        raise ValueError("Cause-data audit blocks training")
    normals = json.loads(normal_manifest.read_text(encoding="utf-8"))
    if normals.get("schema_version") != 1:
        raise ValueError("Unsupported normal manifest")
    records = []
    hashes = {r["sha256"] for r in abnormal}
    ids = {r["record_id"] for r in abnormal}
    for row in normals["records"]:
        r = dict(row)
        if r.get("label") != "normal" or r.get("label_verified") is not True or NORMAL_TAG not in r.get("label_evidence", ""):
            raise ValueError("Normal records require reviewed source ambient evidence")
        if r.get("origin") != "gesl_field" and not (allow_fixture and r.get("origin") == "test_fixture"):
            raise ValueError("Normal records require field provenance")
        if not all(r.get(k) for k in ["parent_family_id", "signature_id", "source_url", "source_component_id"]):
            raise ValueError("Missing normal source metadata")
        path = (normal_manifest.parent / r["csv"]).resolve()
        if not path.is_relative_to(normal_manifest.parent.resolve()):
            raise ValueError("Normal CSV path escapes its manifest directory")
        if d.sha256(path) != r["sha256"] or r["sha256"] in hashes or r["record_id"] in ids:
            raise ValueError("Normal checksum, duplicate content or ID violation")
        trace, matrix = d.read_trace(path, r["angle_unit"], r["sample_interval"], r.get("timestamp_precision", 0), "measurement-context")
        hashes.add(r["sha256"])
        ids.add(r["record_id"])
        records.append({**r, "trace": trace, "features": matrix, "feature_profile": "measurement-context"})
    records += abnormal
    signature_groups = {}
    for r in records:
        signature_groups.setdefault(r["signature_id"], set()).add(r["parent_family_id"])
    if any(len(v) != 1 for v in signature_groups.values()):
        raise ValueError("One source signature cannot appear in different families")
    if any(r["sample_interval"] != 1 / 30 for r in records):
        raise ValueError("Stage 1 supports original 30 Hz context measurements only")
    if len({r["parent_family_id"] for r in records if r["label"] == "normal"}) < 3:
        raise ValueError("Need at least three independent ambient groups")
    return records


def splits(records, folds):
    """Keep provider/month ambient and physical records together, including mixed groups.

    Timing groups are stratified separately so each test fold receives one of the
    few independent timing families. No waveform values or outcomes control splits.
    """
    groups = np.array([r["parent_family_id"] for r in records])
    unique = np.unique(groups)
    strata = ["timing" if any(r["label"] == "sensor" and r["parent_family_id"] == g for r in records)
              else "other" for g in unique]
    if min(strata.count("timing"), strata.count("other")) < folds:
        raise ValueError("Insufficient source families for grouped folds")
    result = []
    for a, b in StratifiedKFold(folds, shuffle=True, random_state=42).split(unique, strata):
        train, test = np.flatnonzero(np.isin(groups, unique[a])), np.flatnonzero(np.isin(groups, unique[b]))
        assert not set(groups[train]) & set(groups[test])
        if any({records[i]["label"] for i in subset} != {"normal", "physical", "sensor"} for subset in [train, test]):
            raise ValueError("A grouped partition lacks normal, physical or timing examples")
        result.append((train, test))
    return result


def detector_labels(records):
    return np.array(["normal" if r["label"] == "normal" else "abnormal" for r in records])


def detector_weights(records):
    labels = detector_labels(records)
    families = {c: {r["parent_family_id"] for r, label in zip(records, labels) if label == c} for c in DETECTION_CLASSES}
    return np.array([1 / (len(families[label]) * sum(other["parent_family_id"] == r["parent_family_id"] and other_label == label
                     for other, other_label in zip(records, labels))) for r, label in zip(records, labels)])


def fit_detector(records, leaf):
    model = RandomForestClassifier(n_estimators=300, min_samples_leaf=leaf, random_state=42, n_jobs=1)
    model.fit(np.concatenate([r["features"] for r in records]), detector_labels(records), sample_weight=detector_weights(records))
    return model


def abnormal_scores(model, records):
    matrix = np.concatenate([r["features"] for r in records])
    return model.predict_proba(matrix)[:, list(model.classes_).index("abnormal")]


def detection_policy(labels, scores):
    """Maximum coverage per returned class subject to observed inner precision >=95%."""
    normal_cutoff, abnormal_cutoff = -1., 2.
    for cutoff in np.unique(scores):
        keep = scores <= cutoff
        if np.mean(labels[keep] == "normal") >= .95:
            normal_cutoff = float(cutoff)
        keep = scores >= cutoff
        if abnormal_cutoff == 2 and np.mean(labels[keep] == "abnormal") >= .95:
            abnormal_cutoff = float(cutoff)
    if normal_cutoff >= abnormal_cutoff:
        return {"normal_max": -1., "abnormal_min": 2.}
    return {"normal_max": normal_cutoff, "abnormal_min": abnormal_cutoff}


def select_detector(records):
    family_count = len({r["parent_family_id"] for r in records if r["label"] == "sensor"})
    partitions = splits(records, min(3, family_count))
    labels = detector_labels(records)
    best = (-1., None, None)
    for leaf in [1, 3, 5]:
        scores = np.zeros(len(records))
        for a, b in partitions:
            model = fit_detector([records[i] for i in a], leaf)
            scores[b] = abnormal_scores(model, [records[i] for i in b])
        quality = f1_score(labels, np.where(scores >= .5, "abnormal", "normal"), average="macro")
        if quality > best[0]:
            best = quality, leaf, scores
    return best[1], detection_policy(labels, best[2])


def detection_decision(score, policy):
    if score <= policy["normal_max"]:
        return "normal"
    if score >= policy["abnormal_min"]:
        return "abnormal"
    return "uncertain"


def route(bundle, matrix):
    sample = [{"features": matrix}]
    score = float(abnormal_scores(bundle["detector"], sample)[0])
    detected = detection_decision(score, bundle["detection_policy"])
    result = {"status": "uncertain" if detected == "uncertain" else "complete",
              "category": "normal" if detected == "normal" else None,
              "detection": {"decision": detected, "abnormal_score": score,
                            "thresholds": {k: v if 0 <= v <= 1 else None for k, v in bundle["detection_policy"].items()}},
              "diagnosis": None, "reason": None, "physical_location": None,
              "model_version": bundle["version"], "experimental": True, "score_kind": "uncalibrated"}
    if detected == "uncertain":
        result["reason"] = "Insufficient evidence to decide whether the window is abnormal."
    elif detected == "abnormal":
        cause = bundle["cause"]
        probabilities = d.probabilities(cause["model"], sample)[0]
        category = d.CLASSES[int(probabilities.argmax())]
        accepted = float(probabilities.max()) >= cause["threshold"]
        result.update(category=category if accepted else None, status="complete" if accepted else "uncertain",
                      reason=None if accepted else "Abnormal window; cause uncertain under the validation policy.",
                      diagnosis={"decision": category if accepted else "uncertain", "score_class": category,
                                 "raw_score": float(probabilities.max()), "threshold": cause["threshold"] if cause["threshold"] <= 1 else None,
                                 "model_version": cause["version"]})
    return result


def predict(bundle, path, unit):
    trace, matrix = d.read_trace(Path(path), unit, 1 / 30, .001, "measurement-context")
    result = route(bundle, matrix)
    result.update(diagnosed_at_utc=datetime.now(timezone.utc).isoformat(),
                  observation_window={"start": float(trace.elapsed_seconds.iloc[0]), "end": float(trace.elapsed_seconds.iloc[-1])},
                  sample_count=len(trace), ground_truth=None)
    return result, trace


def train(normal_manifest, cause_manifest, cause_run, protocol, output):
    if output.exists():
        raise ValueError("Use a new output directory")
    protocol_hash = d.sha256(protocol)
    data_hashes = {"normal": d.sha256(normal_manifest), "cause": d.sha256(cause_manifest)}
    records = load_data(normal_manifest, cause_manifest)
    partitions = splits(records, 3)
    rows, fold_reports = [], []
    for fold, (a, b) in enumerate(partitions):
        training = [records[i] for i in a]
        leaf, policy = select_detector(training)
        detector = fit_detector(training, leaf)
        cause_training = [r for r in training if r["label"] != "normal"]
        parameters, threshold = d.select_model(cause_training)
        cause = {"model": d.fit(cause_training, **parameters), "threshold": threshold,
                 "version": f"{VERSION}-cause-outer-{fold}"}
        temporary_bundle = {"version": VERSION, "detector": detector, "cause": cause, "detection_policy": policy}
        for index in b:
            r = records[index]
            result = route(temporary_bundle, r["features"])
            rows.append({"record_id": r["record_id"], "family": r["parent_family_id"], "label": r["label"],
                         "fold": fold, **result})
        fold_reports.append({"fold": fold, "detector_leaf": leaf, "detector_policy": policy,
                             "cause_parameters": parameters, "cause_threshold": threshold,
                             "train_families": sorted({r["parent_family_id"] for r in training}),
                             "test_families": sorted({records[i]["parent_family_id"] for i in b})})
    leaf, policy = select_detector(records)
    cause_metadata = json.loads((cause_run / "model_manifest.json").read_text())
    if cause_metadata["manifest_sha256"] != data_hashes["cause"] or cause_metadata["sklearn_version"] != importlib.metadata.version("scikit-learn"):
        raise ValueError("Saved cause model does not match data/environment")
    cause = joblib.load(cause_run / "model.joblib")
    bundle = {"version": VERSION, "detector": fit_detector(records, leaf), "detection_policy": policy, "cause": cause,
              "features": CONTEXT_FEATURES, "profile": "measurement-context", "status": "experimental",
              "sklearn_version": importlib.metadata.version("scikit-learn"), "protocol_sha256": protocol_hash,
              "data_hashes": data_hashes, "detector_leaf": leaf}
    actual = [r["label"] for r in rows]
    predicted = [r["category"] or "uncertain" for r in rows]
    normal = [r for r in rows if r["label"] == "normal"]
    abnormal = [r for r in rows if r["label"] != "normal"]
    returned = [r for r in rows if r["category"] is not None]
    forced = ["abnormal" if r["detection"]["abnormal_score"] >= .5 else "normal" for r in rows]
    evaluation = {"status": "experimental", "evidence_role": "grouped development; no independent final confirmation",
        "records": len(records), "normal_records": len(normal), "abnormal_records": len(abnormal),
        "families": len({r["parent_family_id"] for r in records}), "folds": fold_reports,
        "detector": {"forced_class_order": DETECTION_CLASSES,
                     "forced_confusion_matrix": confusion_matrix(["normal" if r["label"] == "normal" else "abnormal" for r in rows], forced, labels=DETECTION_CLASSES).tolist(),
                     "abnormal_recall_after_policy": sum(r["detection"]["decision"] == "abnormal" for r in abnormal) / len(abnormal),
                     "normal_false_alarm_rate": sum(r["detection"]["decision"] == "abnormal" for r in normal) / len(normal),
                     "abnormal_missed_as_normal": sum(r["detection"]["decision"] == "normal" for r in abnormal),
                     "normal_decision_rate": sum(r["detection"]["decision"] == "normal" for r in normal) / len(normal),
                     "uncertain_count": sum(r["detection"]["decision"] == "uncertain" for r in rows)},
        "pipeline": {"row_order": ["normal", "physical", "sensor"], "column_order": OUTPUT_CLASSES,
                     "confusion_matrix": confusion_matrix(actual, predicted, labels=OUTPUT_CLASSES).tolist()[:3],
                     "coverage": len(returned) / len(rows),
                     "accuracy_among_returned": sum(r["category"] == r["label"] for r in returned) / len(returned) if returned else None,
                     "correct_fraction_all_inputs": sum(a == b for a, b in zip(actual, predicted)) / len(rows)},
        "limitations": ["Source ambient labels are not independent healthy-sensor annotations", "Only three timing families",
                        "Normal versus abnormal channel/window selection differs", "Potential collection and provider confounding",
                        "Uncalibrated scores; validation precision is not a guarantee", "60-second uploaded windows, not continuous detection"],
        "protocol_sha256": protocol_hash, "data_hashes": data_hashes}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="stage1-", dir=output.parent))
    try:
        if data_hashes != {"normal": d.sha256(normal_manifest), "cause": d.sha256(cause_manifest)} or protocol_hash != d.sha256(protocol):
            raise ValueError("Data/protocol changed during training")
        joblib.dump(bundle, temporary / "model.joblib")
        restored = joblib.load(temporary / "model.joblib")
        np.testing.assert_array_equal(abnormal_scores(bundle["detector"], records), abnormal_scores(restored["detector"], records))
        d.save_json(temporary / "evaluation.json", evaluation)
        d.save_json(temporary / "predictions.json", rows)
        d.save_json(temporary / "model_manifest.json", {k: v for k, v in bundle.items() if k not in {"detector", "cause"}})
        for path, name in [(protocol, "protocol.json"), (normal_manifest, "normal_manifest.json"), (cause_manifest, "cause_manifest.json")]:
            shutil.copyfile(path, temporary / name)
        shutil.copyfile(Path(__file__), temporary / "stage1_source.py")
        temporary.rename(output)
    except Exception:
        shutil.rmtree(temporary)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("normal_manifest", type=Path)
    parser.add_argument("cause_manifest", type=Path)
    parser.add_argument("--cause-run", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    train(args.normal_manifest, args.cause_manifest, args.cause_run, args.protocol, args.output)
