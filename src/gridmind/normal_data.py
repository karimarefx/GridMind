"""Curate a source-labeled ambient pilot without outcome-driven channel selection."""
import argparse
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from .diagnosis import read_trace, save_json, sha256
from .gesl import read_archive

NORMAL_TAG = "State::Steady State::Nonspecific Steady State"


def prepare(downloads: Path, destination: Path, signatures: list[str]) -> None:
    if destination.exists():
        raise ValueError("Use a new manifest path; existing curation is preserved")
    records, review = [], []
    for signature in signatures:
        archive = downloads / f"sigId-{signature}.zip"
        frame, metadata, waveform = read_archive(archive)
        if metadata.get("Event Tags", "").strip() != NORMAL_TAG:
            raise ValueError(f"{signature}: requires an exclusive source ambient tag")
        if metadata.get("Data Source") not in {"Provider 9", "Provider 10"}:
            raise ValueError("Only the inspected PNNL ambient collection is supported")
        if len(frame) != 1800:
            raise ValueError("Pilot requires complete one-minute records; no segment selection")
        # Fixed lexicographic first complete channel; not the quietest channel.
        reasons = []
        for column in sorted(c for c in frame if c.endswith("_vp_a")):
            component = column.removesuffix("_vp_a")
            fields = {"angle": column, "frequency": component + "_f",
                      "voltage_magnitude": component + "_vp_m",
                      "current_magnitude": component + "_ip_m", "current_angle": component + "_ip_a"}
            if not set(fields.values()).issubset(frame):
                reasons.append({"channel": column, "reason": "Missing required channels"})
                continue
            trace = pd.DataFrame({"elapsed_seconds": frame.Time.to_numpy() - frame.Time.iloc[0],
                                  "reconstructed": 0, **{k: frame[v].to_numpy() for k, v in fields.items()}})
            from .diagnosis_context import context_features
            try:
                context_features(trace, "degree", 1 / 30)
                t = trace.elapsed_seconds.to_numpy(float)
                if not np.isfinite(t).all() or np.any(np.diff(t) <= 0) or np.max(abs(t - np.arange(1800) / 30)) > .00100001:
                    raise ValueError("Invalid or unsupported waveform timestamps")
            except ValueError as error:
                reasons.append({"channel": column, "reason": str(error)})
                continue
            break
        else:
            raise ValueError(f"{signature}: no complete valid measurement channel")
        path = destination.parent / "records" / f"gesl-{signature}-{column}-normal.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise ValueError("Trace already exists")
        trace.to_csv(path, index=False)
        read_trace(path, "degree", 1 / 30, .001, "measurement-context")
        source = "east" if metadata["Data Source"] == "Provider 9" else "west"
        family = f"physical-{source}-{metadata['Event Date'][:7]}"
        # Reuse the same conservative provider/month group IDs as physical events.
        records.append({"record_id": path.stem, "label": "normal", "label_verified": True,
                        "parent_family_id": family, "signature_id": signature,
                        "label_evidence": NORMAL_TAG + "; exclusive source tag; complete first valid PMU; measurement integrity checked",
                        "label_scope": "Source-labeled ambient operation, not independently confirmed healthy sensors",
                        "source_url": "https://gsl.ornl.gov/dashboard", "origin": "gesl_field",
                        "csv": str(path.relative_to(destination.parent)), "sha256": sha256(path),
                        "sample_interval": 1 / 30, "timestamp_precision": .001, "angle_unit": "degree",
                        "channel_id": column, "source_component_id": component,
                        "source_archive_sha256": sha256(archive), "source_samples": [0, 1800]})
        copied = destination.parent.parent / "normal_source_downloads" / archive.name
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive, copied)
        review.append({"signature_id": signature, "metadata": metadata, "waveform": waveform,
                       "channel": column, "skipped_channels": reasons, "source_sha256": sha256(archive),
                       "waveform_rate_hz": 30, "metadata_rate_mismatch": float(metadata["Rate (Hz)"]) != 30,
                       "frequency_range_hz": float(np.ptp(trace.frequency)),
                       "voltage_relative_range": float(np.ptp(trace.voltage_magnitude) / np.median(trace.voltage_magnitude)),
                       "review_basis": "Exclusive ambient tag, source collection documentation and numerical integrity; visual review recorded separately"})
    save_json(destination, {"schema_version": 1, "records": records,
              "limitations": ["Source-level ambient labels do not establish absence of all sensor faults",
                              "Normal channel selection differs from event-centered abnormal pilot selection",
                              "Provider/month groups are conservative assumptions, not proven event identities"]})
    save_json(destination.parent / "normal_review.json", {"records": review})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("downloads", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--signatures", nargs="+", required=True)
    args = parser.parse_args()
    prepare(args.downloads, args.output, args.signatures)
