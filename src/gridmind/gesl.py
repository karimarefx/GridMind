"""Inspect authenticated GESL archives and curate one phase-angle window per event.

Downloads are obtained through GESL's supported website. This module handles the
observed archive formats without credentials, HTTP sessions, or executable content.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .diagnosis import read_trace, save_json, sha256


def source_label(tags: str) -> str:
    if "Instrument::Timing" in tags:
        return "sensor"
    physical_tags = ["State::Change State::Trip", "Events::Fault::", "Events::Equipment Failure::",
                     "Events::External::Lightning Strike", "Events::System Event/Condition::Frequency Deviation",
                     "Events::System Event/Condition::Oscillation"]
    return "physical" if any(tag in tags for tag in physical_tags) else "unsupported"


def read_archive(path: Path) -> tuple[pd.DataFrame, dict, str]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        metadata_name = next(n for n in names if n.endswith("-Metadata.csv"))
        reader = csv.DictReader(io.StringIO(archive.read(metadata_name).decode("utf-8-sig")), skipinitialspace=True)
        metadata = {k.strip(): str(v).strip() for k, v in next(reader).items() if k is not None}
        nested = [n for n in names if n.endswith(".zip")]
        if nested:
            with zipfile.ZipFile(io.BytesIO(archive.read(nested[0]))) as inner:
                waveform_name = next(n for n in inner.namelist() if n.endswith(".csv"))
                payload = inner.read(waveform_name)
        else:
            waveform_name = next(n for n in names if n.endswith(".csv") and "Metadata" not in n)
            payload = archive.read(waveform_name)
    frame = pd.read_csv(io.BytesIO(payload))
    frame.columns = frame.columns.str.replace(".", "_", regex=False)
    if "Time" not in frame:
        raise ValueError("Archive has no observed Time column")
    return frame, metadata, waveform_name


def candidate_window(frame: pd.DataFrame) -> tuple[str, int, float]:
    """Use the same selection rule for both labels; it is a curation aid only.

    Find the largest circular phase step with a complete finite 90-sample window.
    Source annotations and visual review still determine whether its label applies.
    """
    candidates = []
    for column in frame.columns:
        if not column.endswith("_vp_a"):
            continue
        angle = frame[column].to_numpy(float)
        if len(angle) < 90:
            continue
        finite = pd.Series(np.isfinite(angle).astype(int)).rolling(90).sum().to_numpy()
        centers = np.arange(45, len(angle) - 44)
        valid = finite[centers + 44] == 90
        jumps = np.abs((angle[centers] - angle[centers - 1] + 180) % 360 - 180)
        jumps[~valid] = -1
        best = int(np.argmax(jumps))
        if jumps[best] >= 0:
            candidates.append((float(jumps[best]), column, int(centers[best])))
    if not candidates:
        raise ValueError("No finite phase-angle segment with 90 samples")
    jump, column, center = max(candidates)
    return column, center, jump


def inspect(source: Path, output: Path) -> None:
    candidates = []
    for path in sorted(source.glob("sigId-*.zip")):
        frame, metadata, waveform = read_archive(path)
        tags = metadata.get("Event Tags", "")
        timing = "Instrument::Timing" in tags
        mixed = timing and "Power system event::" in tags
        sensor = metadata.get("Sensor", "")
        dt = float(np.median(np.diff(frame.Time)))
        hz = 60 if dt < .025 else 30
        # These sources report timestamps rounded to 0.001 seconds.
        channel, center, jump = candidate_window(frame)
        window = frame.iloc[center - 45:center + 45]
        time = window.Time.to_numpy(float)
        residual = np.max(np.abs(time - time[0] - np.arange(90) / hz))
        candidates.append({"signature_id": metadata["ID"], "archive": path.name,
                           "source_sha256": sha256(path), "waveform": waveform,
                           "metadata": metadata, "proposed_label": source_label(tags),
                           "mixed_event_tags": mixed, "sensor": sensor, "sample_rate": hz,
                           "timestamp_precision": .001, "cadence_error_seconds": float(residual),
                           "channel": channel, "center": center, "start_sample": center - 45,
                           "end_sample": center + 45, "jump_degree": jump,
                           "reviewed": False, "parent_family_id": "", "review_reason": ""})
    save_json(output, {"schema_version": 1, "selection": "largest finite circular phase step; same rule for both classes",
                       "candidates": candidates})


def prepare(source: Path, review: Path, output: Path) -> None:
    document = json.loads(review.read_text(encoding="utf-8"))
    records, excluded = [], []
    for item in document["candidates"]:
        if item.get("reviewed") is not True:
            excluded.append({"signature_id": item["signature_id"], "reason": item.get("review_reason") or "Not reviewed"})
            continue
        if not item.get("review_reason") or not item.get("parent_family_id"):
            raise ValueError("Reviewed records require review_reason and parent_family_id")
        if item["mixed_event_tags"] or item["sample_rate"] != 30:
            raise ValueError("Initial import requires unmixed 30 Hz records")
        if not str(item["signature_id"]).isdigit() or not re.fullmatch(r"P\d+_vp_a", item["channel"]):
            raise ValueError("Unexpected source signature or phase-angle channel identifier")
        path = source / item["archive"]
        if not path.resolve().is_relative_to(source.resolve()) or sha256(path) != item["source_sha256"]:
            raise ValueError("Source path or archive checksum changed")
        frame, metadata, _ = read_archive(path)
        tags = metadata.get("Event Tags", "")
        expected_label = source_label(tags)
        if expected_label == "unsupported" or item["proposed_label"] != expected_label or (expected_label == "sensor" and "Power system event::" in tags):
            raise ValueError("Reviewed label conflicts with archive tags")
        selected = frame.iloc[item["start_sample"]:item["end_sample"]]
        if len(selected) != 90:
            raise ValueError("Reviewed segment must contain 90 original samples")
        name = f"gesl-{item['signature_id']}-{item['channel']}"
        trace_path = output.parent / "records" / (name + ".csv")
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"elapsed_seconds": selected.Time.to_numpy() - selected.Time.iloc[0],
                      "angle": selected[item["channel"]].to_numpy(), "reconstructed": 0}).to_csv(trace_path, index=False)
        read_trace(trace_path, "degree", 1 / 30, .001)
        records.append({"record_id": name, "parent_family_id": item["parent_family_id"],
                        "signature_id": item["signature_id"], "label": item["proposed_label"],
                        "label_verified": True, "label_evidence": metadata["Event Tags"] + "; " + item["review_reason"],
                        "source_url": "https://gsl.ornl.gov/dq-dashboard" if item["proposed_label"] == "sensor" else "https://gsl.ornl.gov/dashboard",
                        "origin": "gesl_field", "csv": str(trace_path.relative_to(output.parent)),
                        "sha256": sha256(trace_path), "sample_interval": 1 / 30, "timestamp_precision": .001,
                        "angle_unit": "degree", "channel_id": item["channel"],
                        "source_component_id": item["channel"].split("_")[0],
                        "source_archive_sha256": item["source_sha256"],
                        "source_samples": [item["start_sample"], item["end_sample"]]})
    save_json(output, {"schema_version": 1, "records": records})
    save_json(output.parent / "import_report.json", {"records": len(records), "excluded": excluded,
              "review_sha256": sha256(review), "limitations": [
                  "Convenience sample of physical events from the first provider pages",
                  "Offline event-centered windows; not validated as a streaming detector",
                  "Same largest-phase-step segment selection applied to both classes",
                  "Source-independent family identity cannot be proven from anonymized metadata"]})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("inspect")
    audit.add_argument("source", type=Path)
    audit.add_argument("--output", type=Path, required=True)
    convert = sub.add_parser("prepare")
    convert.add_argument("source", type=Path)
    convert.add_argument("review", type=Path)
    convert.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "inspect":
        inspect(args.source, args.output)
    else:
        prepare(args.source, args.review, args.output)


if __name__ == "__main__":
    main()
