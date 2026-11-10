import numpy as np
import pytest

from gridmind import stage1 as s
from gridmind.diagnosis_context import CONTEXT_FEATURES


def records():
    rows = []
    rng = np.random.default_rng(31)
    for label in ["normal", "physical", "sensor"]:
        for group in range(6):
            rows.append({"record_id": f"{label}-{group}", "label": label,
                         "parent_family_id": f"timing-{group}" if label == "sensor" else f"provider-month-{group}",
                         "features": rng.normal(label == "sensor", .02, (1, len(CONTEXT_FEATURES)))})
    return rows


def test_mixed_normal_physical_families_never_leak():
    data = records()
    for a, b in s.splits(data, 3):
        assert not {data[i]["parent_family_id"] for i in a} & {data[i]["parent_family_id"] for i in b}
        assert {data[i]["label"] for i in b} == {"normal", "physical", "sensor"}


def test_detector_balances_class_and_family():
    data = records()
    data += [dict(data[0], record_id="extra-normal")]
    w = s.detector_weights(data)
    labels = s.detector_labels(data)
    assert w[labels == "normal"].sum() == pytest.approx(1)
    assert w[labels == "abnormal"].sum() == pytest.approx(1)
    assert w[0] == pytest.approx(w[-1])


def test_uncertainty_policy_and_routing():
    policy = s.detection_policy(np.array(["normal", "normal", "abnormal", "abnormal"]), np.array([.1, .2, .8, .9]))
    assert s.detection_decision(.1, policy) == "normal"
    assert s.detection_decision(.5, policy) == "uncertain"
    assert s.detection_decision(.9, policy) == "abnormal"
    infeasible = s.detection_policy(np.array(["normal", "abnormal"]), np.array([.5, .5]))
    assert s.detection_decision(.5, infeasible) == "uncertain"


class FixedModel:
    classes_ = np.array(["abnormal", "normal"])
    def __init__(self, score): self.score = score
    def predict_proba(self, x): return np.tile([self.score, 1-self.score], (len(x), 1))


def test_normal_and_uncertain_do_not_call_cause_classifier():
    for score, status in [(.1, "normal"), (.5, "uncertain")]:
        bundle = {"version": s.VERSION, "detector": FixedModel(score),
                  "detection_policy": {"normal_max": .2, "abnormal_min": .8}, "cause": None}
        result = s.route(bundle, np.zeros((1, len(CONTEXT_FEATURES))))
        assert result["detection"]["decision"] == status
        assert result["diagnosis"] is None
        assert result["category"] == ("normal" if status == "normal" else None)
