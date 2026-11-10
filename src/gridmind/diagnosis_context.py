"""Measurement-context features and reproducible 60-second GESL source extraction.

This is an experimental engineering extension, not a reproduction of a paper.
No synthetic anomalies, source metadata, identifiers or PMU counts are features.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

CONTEXT_VERSION = "pmu-timing-rf-v3"
CONTEXT_FEATURES = ["phase_rate_std", "phase_rate_max", "phase_rate_p99", "phase_rate_crest",
                    "phase_rate_top3_energy", "phase_impulses_per_minute", "impulse_interval_cv",
                    "frequency_range", "frequency_step_max", "frequency_step_crest",
                    "frequency_endpoint_change", "phase_frequency_residual_rms", "phase_frequency_residual_max",
                    "voltage_relative_range", "voltage_relative_step_max", "voltage_endpoint_change",
                    "current_relative_range", "current_relative_step_max", "current_endpoint_change",
                    "voltage_current_angle_range", "voltage_current_angle_step_max",
                    "phase_event_voltage_change", "phase_event_current_change"]
REQUIRED = ["frequency", "voltage_magnitude", "current_magnitude", "current_angle"]


def context_features(trace: pd.DataFrame, unit: str, interval: float) -> np.ndarray:
    if unit not in {"degree", "radian"}:
        raise ValueError("angle_unit must be degree or radian")
    if not .032 < interval < .034 or len(trace) != 1800:
        raise ValueError("Measurement-context profile requires 1800 original samples at 30 Hz")
    if not set(REQUIRED).issubset(trace):
        raise ValueError("Measurement-context requires frequency, voltage/current magnitudes and current angle")
    channels = trace[["angle", *REQUIRED]].to_numpy(float)
    if not np.isfinite(channels).all() or (trace.voltage_magnitude <= 0).any() or (trace.current_magnitude < 0).any():
        raise ValueError("Context channels must be finite with positive voltage and nonnegative current magnitude")
    angle, frequency, voltage, current, current_angle = channels.T
    if unit == "degree":
        angle, current_angle = np.deg2rad(angle), np.deg2rad(current_angle)
    phase = np.unwrap(angle - angle[0])
    rate = np.diff(phase) / (2 * np.pi * interval)
    residual_rate = rate - np.median(rate)
    magnitude = abs(residual_rate)
    energy = residual_rate ** 2
    eps = 1e-8
    mad = np.median(magnitude)
    # Fixed robust impulse criterion and 0.25-second refractory interval.
    candidates = np.flatnonzero(magnitude > max(8 * mad, .005))
    pulses = []
    for index in candidates:
        if not pulses or index - pulses[-1] > round(.25 / interval):
            pulses.append(int(index))
        elif magnitude[index] > magnitude[pulses[-1]]:
            pulses[-1] = int(index)
    gaps = np.diff(pulses) * interval
    gap_cv = gaps.std() / gaps.mean() if len(gaps) >= 2 else 0.
    frequency_step = np.diff(frequency)
    # Derivative-derived frequency deviation versus reported frequency deviation;
    # median removal avoids a nominal-frequency or static reference assumption.
    reported = (frequency[:-1] + frequency[1:]) / 2
    residual = residual_rate - (reported - np.median(reported))
    v = voltage / np.median(voltage)
    current_scale = max(float(np.median(current)), 1e-8)
    i = current / current_scale
    relative = np.unwrap(angle - current_angle)
    event = int(np.argmax(magnitude)) + 1
    # Source selection centers the phase event. Handle edge maxima consistently.
    event = int(np.clip(event, 30, len(trace) - 31))
    def endpoint(x):
        return abs(np.median(x[-30:]) - np.median(x[:30]))
    def event_change(x):
        return abs(np.median(x[event:event + 30]) - np.median(x[event - 30:event]))
    values = [residual_rate.std(), magnitude.max(), np.quantile(magnitude, .99),
              magnitude.max() / (np.sqrt(energy.mean()) + eps),
              np.sort(energy)[-3:].sum() / (energy.sum() + eps ** 2),
              len(pulses) * 60 / (len(trace) * interval), gap_cv,
              np.ptp(frequency), abs(frequency_step).max(),
              abs(frequency_step).max() / (np.sqrt(np.mean(frequency_step ** 2)) + eps),
              endpoint(frequency), np.sqrt(np.mean(residual ** 2)), abs(residual).max(),
              np.ptp(v), abs(np.diff(v)).max(), endpoint(v),
              np.ptp(i), abs(np.diff(i)).max(), endpoint(i),
              np.ptp(relative), abs(np.diff(relative)).max(), event_change(v), event_change(i)]
    result = np.asarray([values])
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite context features")
    return result


def prepare(source: Path, original_manifest: Path, output: Path) -> None:
    """Extend the unchanged pilot events to one minute on their original channel."""
    from .diagnosis import read_trace, save_json, sha256
    from .gesl import read_archive, source_label
    if output.exists():
        raise ValueError("Use a new manifest path to preserve existing curation")
    document = json.loads(original_manifest.read_text(encoding="utf-8"))
    records = []
    for original in document["records"]:
        archive = source / f"sigId-{original['signature_id']}.zip"
        if sha256(archive) != original["source_archive_sha256"]:
            raise ValueError("Original source archive checksum changed")
        frame, metadata, _ = read_archive(archive)
        if source_label(metadata["Event Tags"]) != original["label"]:
            raise ValueError("Source label changed")
        center = sum(original["source_samples"]) // 2
        start = max(0, min(center - 900, len(frame) - 1800))
        selected = frame.iloc[start:start + 1800]
        component = original["source_component_id"]
        trace = pd.DataFrame({"elapsed_seconds": selected.Time.to_numpy() - selected.Time.iloc[0],
                              "angle": selected[original["channel_id"]].to_numpy(), "reconstructed": 0})
        for destination, suffix in [("frequency", "f"), ("voltage_magnitude", "vp_m"),
                                    ("current_magnitude", "ip_m"), ("current_angle", "ip_a")]:
            trace[destination] = selected[f"{component}_{suffix}"].to_numpy()
        path = output.parent / "records" / f"{original['record_id']}-context.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise ValueError("Context trace already exists")
        trace.to_csv(path, index=False)
        read_trace(path, original["angle_unit"], original["sample_interval"], original.get("timestamp_precision", 0), "measurement-context")
        records.append({**original, "csv": str(path.relative_to(output.parent)), "sha256": sha256(path),
                        "record_id": original["record_id"] + "-context", "source_samples": [start, start + 1800],
                        "original_record_id": original["record_id"],
                        "context_policy": "60 seconds centered at unchanged pilot phase candidate, clipped to source bounds"})
    save_json(output, {"schema_version": 1, "original_manifest_sha256": sha256(original_manifest),
                       "records": records, "limitations": ["Recording-level labels; exact channel/interval not independently annotated",
                       "Same previously examined event families; development data only"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("original_manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.original_manifest, args.output)
