"""Measurement-context invariants and source extraction; not model effectiveness tests."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from gridmind import diagnosis as d
from gridmind import diagnosis_context as c


def trace(seed=0, jump=False):
    time = np.arange(1800) / 30
    rng = np.random.default_rng(seed)
    angle = time * .01 + rng.normal(0, 1e-5, len(time))
    if jump:
        angle += .1 * (np.arange(1800) // 450)
    return pd.DataFrame({"elapsed_seconds": time, "angle": angle, "reconstructed": 0,
                         "frequency": 60 + rng.normal(0, 1e-5, len(time)),
                         "voltage_magnitude": 1 + rng.normal(0, 1e-5, len(time)),
                         "current_magnitude": 2 + rng.normal(0, 1e-5, len(time)),
                         "current_angle": angle - .3})


def test_context_reference_units_magnitude_scaling_and_recurrence():
    frame = trace(jump=True)
    actual = c.context_features(frame, "radian", 1 / 30)
    assert actual.shape == (1, len(c.CONTEXT_FEATURES))
    rotated = frame.copy()
    for column in ["angle", "current_angle"]:
        rotated[column] = (rotated[column] + 1.9 + np.pi) % (2 * np.pi) - np.pi
    rotated.voltage_magnitude *= 230000
    rotated.current_magnitude *= 300
    np.testing.assert_allclose(actual, c.context_features(rotated, "radian", 1 / 30), rtol=1e-7, atol=1e-8)
    degrees = frame.copy()
    degrees[["angle", "current_angle"]] *= 180 / np.pi
    np.testing.assert_allclose(actual, c.context_features(degrees, "degree", 1 / 30), rtol=1e-7, atol=1e-8)
    assert actual[0, c.CONTEXT_FEATURES.index("phase_impulses_per_minute")] == 3
    assert actual[0, c.CONTEXT_FEATURES.index("impulse_interval_cv")] == 0
    # Source identifiers and provider metadata cannot enter this representation.
    frame["provider"] = "untrusted arbitrary string"
    np.testing.assert_array_equal(actual, c.context_features(frame, "radian", 1 / 30))


@pytest.mark.parametrize("change", ["nan", "missing", "negative_voltage", "short", "cadence"])
def test_context_rejects_invalid_measurements(change):
    frame = trace()
    interval = 1 / 30
    if change == "nan": frame.loc[30, "frequency"] = np.nan
    elif change == "missing": frame = frame.drop(columns="current_angle")
    elif change == "negative_voltage": frame.loc[30, "voltage_magnitude"] = 0
    elif change == "short": frame = frame.iloc[:90]
    else: interval = 1 / 60
    with pytest.raises(ValueError):
        c.context_features(frame, "radian", interval)


def test_context_training_saved_roundtrip_and_feature_schema(tmp_path, monkeypatch):
    records = []
    for label in d.CLASSES:
        for family in range(3):
            path = tmp_path / f"{label}-{family}.csv"
            trace(family + (label == "sensor") * 10, label == "sensor").to_csv(path, index=False)
            records.append({"record_id": path.stem, "signature_id": path.stem, "parent_family_id": path.stem,
                            "csv": path.name, "sha256": d.sha256(path), "label": label, "label_verified": True,
                            "label_evidence": "Instrument::Timing synthetic fixture" if label == "sensor" else "physical fixture",
                            "source_url": "test://fixture", "origin": "test_fixture", "angle_unit": "radian",
                            "sample_interval": 1 / 30, "channel_id": "test", "source_component_id": "test"})
    manifest = tmp_path / "manifest.json"
    d.save_json(manifest, {"schema_version": 1, "records": records})
    original_loader, original_rf = d.load_records, d.RandomForestClassifier
    monkeypatch.setattr(d, "load_records", lambda path, **kwargs: original_loader(path, allow_fixture=True, **kwargs))
    monkeypatch.setattr(d, "RandomForestClassifier", lambda **kwargs: original_rf(**{**kwargs, "n_estimators": 5}))
    protocol = Path(__file__).resolve().parents[1] / "reports/diagnosis/v3_protocol.json"
    output = tmp_path / "run"
    d.train(manifest, output, "measurement-context", protocol)
    model = joblib.load(output / "model.joblib")
    assert model["features"] == c.CONTEXT_FEATURES and model["version"] == c.CONTEXT_VERSION
    assert model["context_implementation_sha256"] == d.sha256(output / "diagnosis_context_source.py")
    prediction = d.predict(model, tmp_path / records[0]["csv"], "radian", 1 / 30, "fixture")
    assert prediction["status"] in {"uncertain", "complete"}
    result = json.loads((output / "evaluation.json").read_text())
    for fold in result["folds"]:
        assert not set(fold["test_groups"]) & set(fold["train_groups"])
    assert json.loads((output / "audit.json").read_text())["windows"] == 6
