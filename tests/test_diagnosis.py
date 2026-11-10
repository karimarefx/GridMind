"""Software fixtures exercise contracts; they are not field-data evidence."""
import json

import joblib
import numpy as np
import pandas as pd
import pytest

from gridmind import diagnosis as d


def make_manifest(tmp_path, groups=6):
    records = []
    for label in d.CLASSES:
        for group in range(groups):
            time = np.arange(90) / 30
            rng = np.random.default_rng(group + 100 * (label == "sensor"))
            angle = rng.normal(0, .002, len(time))
            if label == "sensor":
                angle += np.where(time > 1.5, .4, 0)
            path = tmp_path / f"{label}-{group}.csv"
            pd.DataFrame({"elapsed_seconds": time, "angle": angle,
                          "reconstructed": 0}).to_csv(path, index=False)
            records.append({"record_id": path.stem, "parent_family_id": path.stem,
                            "signature_id": path.stem, "label": label, "label_verified": True,
                            "label_evidence": "Instrument::Timing test fixture" if label == "sensor" else "physical test fixture",
                            "source_url": "test://fixture", "origin": "test_fixture",
                            "csv": path.name, "sha256": d.sha256(path), "sample_interval": 1 / 30,
                            "angle_unit": "radian", "channel_id": "angle",
                            "source_component_id": "test-pmu"})
    path = tmp_path / "manifest.json"
    d.save_json(path, {"schema_version": 1, "records": records})
    return path


def test_features_units_wrapping_and_constant():
    radians = np.linspace(3, 3.5, 90)
    wrapped = (radians + np.pi) % (2 * np.pi) - np.pi
    actual = d.features(wrapped, "radian")
    np.testing.assert_allclose(actual, d.features(np.rad2deg(wrapped), "degree"), atol=1e-12)
    expected = pd.Series(radians).rolling(45)
    np.testing.assert_allclose(actual[:, 0], expected.mean().dropna(), atol=1e-12)
    np.testing.assert_allclose(actual[:, 1], expected.std().dropna(), atol=1e-12)
    np.testing.assert_allclose(actual[:, 2], expected.skew().dropna(), atol=1e-9)
    assert np.all(d.features(np.ones(90), "radian")[:, 1:] == 0)
    with pytest.raises(ValueError):
        d.features([np.nan] * 90, "radian")


def test_fixture_never_passes_production_audit(tmp_path):
    path = make_manifest(tmp_path)
    records, audit = d.load_records(path)
    assert not records and audit["status"] == "blocked"
    assert len(audit["rejected"]) == 12
    with pytest.raises(ValueError, match="audit blocks"):
        d.train(path, tmp_path / "model")


def test_manifest_checks_labels_hashes_and_families(tmp_path):
    path = make_manifest(tmp_path)
    records, audit = d.load_records(path, allow_fixture=True)
    assert audit["status"] == "ready"
    for train, test in d.grouped_splits(records, 3):
        assert not ({records[i]["parent_family_id"] for i in train}
                    & {records[i]["parent_family_id"] for i in test})
    value = json.loads(path.read_text())
    value["records"][0]["sha256"] = "wrong"
    value["records"][1]["label_verified"] = False
    d.save_json(path, value)
    _, audit = d.load_records(path, allow_fixture=True)
    assert len(audit["rejected"]) == 2
    assert audit["status"] == "blocked"


def test_group_identity_and_duplicate_content(tmp_path):
    path = make_manifest(tmp_path)
    document = json.loads(path.read_text())
    duplicate = dict(document["records"][0], record_id="duplicate")
    document["records"].append(duplicate)
    d.save_json(path, document)
    _, audit = d.load_records(path, allow_fixture=True)
    assert any("Duplicate trace content" in row["reason"] for row in audit["rejected"])
    document["records"].pop()
    document["records"][1]["signature_id"] = document["records"][0]["signature_id"]
    d.save_json(path, document)
    with pytest.raises(ValueError, match="different parent families"):
        d.load_records(path, allow_fixture=True)


@pytest.mark.parametrize("change", ["missing", "gap", "reconstructed", "short"])
def test_bad_inputs_are_unavailable(tmp_path, change):
    path = make_manifest(tmp_path)
    records, _ = d.load_records(path, allow_fixture=True)
    model = d.fit(records, None, 1)
    bundle = {"version": d.VERSION, "model": model, "threshold": .5, "sample_interval": 1 / 30}
    csv = tmp_path / records[0]["csv"]
    frame = pd.read_csv(csv)
    if change == "missing":
        frame.loc[1, "angle"] = np.nan
    elif change == "gap":
        frame = frame.drop(index=5)
    elif change == "reconstructed":
        frame.loc[1, "reconstructed"] = 1
    else:
        frame = frame.iloc[:20]
    frame.to_csv(csv, index=False)
    result = d.predict(bundle, csv, "radian", 1 / 30, "fixture")
    assert result["status"] == "unavailable"
    assert result["raw_score"] is None


def test_threshold_abstention_and_roundtrip(tmp_path):
    path = make_manifest(tmp_path)
    records, _ = d.load_records(path, allow_fixture=True)
    model = d.fit(records, "balanced", 1)
    bundle = {"version": d.VERSION, "model": model, "threshold": 1.01, "sample_interval": 1 / 30}
    csv = tmp_path / records[0]["csv"]
    before = d.predict(bundle, csv, "radian", 1 / 30, "fixture")
    assert before["status"] == "uncertain"
    assert before["decision_threshold"] is None
    assert d.threshold_for(np.array(["sensor", "physical"]), np.array([[.9, .1], [.1, .9]])) == 1.01
    target = tmp_path / "model.joblib"
    joblib.dump(bundle, target)
    after = d.predict(joblib.load(target), csv, "radian", 1 / 30, "fixture")
    assert before["raw_score"] == after["raw_score"]
    result = d.predict(bundle, csv, "radian", 1 / 60, "fixture")
    assert result["status"] == "unavailable"


def test_rounded_source_timestamps_preserved(tmp_path):
    path = tmp_path / "rounded.csv"
    frame = pd.DataFrame({"elapsed_seconds": np.round(np.arange(90) / 30, 3),
                          "angle": np.arange(90) * .1, "reconstructed": 0})
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="sampling"):
        d.read_trace(path, "degree", 1 / 30)
    trace, _ = d.read_trace(path, "degree", 1 / 30, .001)
    np.testing.assert_array_equal(trace.elapsed_seconds, frame.elapsed_seconds)
    frame.loc[50:, "elapsed_seconds"] += 1 / 30
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="sampling"):
        d.read_trace(path, "degree", 1 / 30, .001)


def test_uneven_families_keep_both_classes_in_each_fold():
    records = [{"label": label, "parent_family_id": f"{label}-{family}"}
               for label in d.CLASSES for family, count in enumerate([1, 2, 8]) for _ in range(count)]
    first = d.grouped_splits(records, 3)
    second = d.grouped_splits(records, 3)
    for (train, test), repeated in zip(first, second):
        assert {records[i]["label"] for i in test} == set(d.CLASSES)
        assert not {records[i]["parent_family_id"] for i in train} & {records[i]["parent_family_id"] for i in test}
        np.testing.assert_array_equal(test, repeated[1])


def test_nested_training_and_dashboard_contract(tmp_path, monkeypatch):
    manifest = make_manifest(tmp_path, groups=5)
    original_loader = d.load_records
    # Explicit test-only fixture injection; production train rejects these files.
    monkeypatch.setattr(d, "load_records", lambda path: original_loader(path, allow_fixture=True))
    original_rf = d.RandomForestClassifier

    def fast_forest(**kwargs):
        kwargs["n_estimators"] = 5
        kwargs["n_jobs"] = 1
        return original_rf(**kwargs)

    monkeypatch.setattr(d, "RandomForestClassifier", fast_forest)
    output = tmp_path / "run"
    d.train(manifest, output)
    evaluation = json.loads((output / "evaluation.json").read_text())
    assert len(evaluation["folds"]) == 5
    for fold in evaluation["folds"]:
        assert not set(fold["train_groups"]) & set(fold["test_groups"])
    dashboard = output / "dashboard" / "diagnosis"
    episodes = json.loads((dashboard / "event_episodes.json").read_text())
    predictions = json.loads((dashboard / "diagnosis_predictions.json").read_text())
    assert len(episodes) == len(predictions) == 10
    for episode, prediction in zip(episodes, predictions):
        assert episode["episode_id"] == prediction["episode_id"]
        assert episode["input_origin"] == "test_fixture"
        assert prediction["class_mapping"] and prediction["physical_location"] is None
        assert prediction["decision_threshold"] is None or 0 <= prediction["decision_threshold"] <= 1
        assert (output / "dashboard" / episode["trace_path"]).exists()
    with pytest.raises(ValueError, match="new output"):
        d.train(manifest, output)
