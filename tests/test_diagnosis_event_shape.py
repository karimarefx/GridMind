"""Invariants and training contracts; synthetic fixtures are not effectiveness evidence."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from gridmind import diagnosis as d
from test_diagnosis import make_manifest


def test_reference_units_and_wrapping_invariance():
    rng = np.random.default_rng(71)
    angle = np.linspace(170, 210, 90) + rng.normal(0, .01, 90)
    angle[45:] += 8
    reference = d.features(angle, "degree", "event-shape")
    assert reference.shape == (1, len(d.EVENT_FEATURES))
    for offset in [90, 180, 270, 720]:
        wrapped = (angle + offset + 180) % 360 - 180
        np.testing.assert_allclose(reference, d.features(wrapped, "degree", "event-shape"), rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(reference, d.features(np.deg2rad(angle), "radian", "event-shape"))


def test_jump_is_preserved_and_constant_is_finite():
    smooth = np.arange(90) * .001
    jumped = smooth.copy()
    jumped[45:] += .2
    step = d.event_features(jumped, "radian")[0]
    steady = d.event_features(smooth, "radian")[0]
    assert step[d.EVENT_FEATURES.index("increment_max")] > .19
    assert step[d.EVENT_FEATURES.index("top3_energy_fraction")] > .99
    assert steady[d.EVENT_FEATURES.index("increment_max")] < 1e-12
    assert np.all(d.event_features(np.ones(90), "radian") == 0)
    for invalid in [np.ones(89), np.ones(91), np.full(90, np.nan)]:
        with pytest.raises(ValueError, match="exactly 90"):
            d.event_features(invalid, "radian")


def test_family_and_class_weighting():
    records = []
    for label, sizes in [("physical", [1, 3, 8]), ("sensor", [1, 5])]:
        for family, size in enumerate(sizes):
            records.extend({"label": label, "parent_family_id": f"{label}-{family}",
                            "features": np.zeros((1, len(d.EVENT_FEATURES))), "feature_profile": "event-shape"}
                           for _ in range(size))
    weights = d.training_weights(records)
    for label, count in [("physical", 3), ("sensor", 2)]:
        mask = np.array([r["label"] == label for r in records])
        assert weights[mask].sum() == pytest.approx(1)
        for family in {r["parent_family_id"] for r in records if r["label"] == label}:
            assert weights[[r["parent_family_id"] == family for r in records]].sum() == pytest.approx(1 / count)


def test_v2_grouped_training_saved_inference_and_legacy_compatibility(tmp_path, monkeypatch):
    manifest = make_manifest(tmp_path, groups=3)
    original_loader, original_rf = d.load_records, d.RandomForestClassifier
    monkeypatch.setattr(d, "load_records", lambda path, **kwargs: original_loader(path, allow_fixture=True, **kwargs))
    monkeypatch.setattr(d, "RandomForestClassifier", lambda **kwargs: original_rf(**{**kwargs, "n_estimators": 5}))
    protocol = Path(__file__).resolve().parents[1] / "reports/diagnosis/v2_protocol.json"
    output = tmp_path / "v2"
    with pytest.raises(ValueError, match="frozen"):
        d.train(manifest, output, "event-shape")
    d.train(manifest, output, "event-shape", protocol)
    evaluation = json.loads((output / "evaluation.json").read_text())
    assert evaluation["evidence_role"].startswith("development")
    assert evaluation["protocol_sha256"] == d.sha256(protocol)
    for fold in evaluation["folds"]:
        assert not set(fold["train_groups"]) & set(fold["test_groups"])
    predictions = json.loads((output / "dashboard/diagnosis/diagnosis_predictions.json").read_text())
    assert all(p["model_version"].startswith(d.EVENT_VERSION) for p in predictions)
    bundle = joblib.load(output / "model.joblib")
    document = json.loads(manifest.read_text())
    record = document["records"][0]
    csv = tmp_path / record["csv"]
    result = d.predict(bundle, csv, "radian", 1 / 30, "fixture")
    assert result["status"] in {"complete", "uncertain"}
    frame = pd.read_csv(csv)
    frame.angle += np.pi / 2
    rotated = tmp_path / "rotated.csv"
    frame.to_csv(rotated, index=False)
    after = d.predict(bundle, rotated, "radian", 1 / 30, "fixture")
    assert after["raw_score"] == pytest.approx(result["raw_score"], abs=1e-12)
    assert after["score_class"] == result["score_class"]
    # Existing v1 features and model bundles retain their default interpretation.
    legacy, _ = original_loader(manifest, allow_fixture=True)
    legacy_bundle = {"version": d.VERSION, "model": d.fit(legacy, None, 1),
                     "threshold": 1.01, "sample_interval": 1 / 30}
    assert d.predict(legacy_bundle, csv, "radian", 1 / 30, "legacy")["status"] == "uncertain"
