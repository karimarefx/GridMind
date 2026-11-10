import io
import json
import zipfile

import numpy as np
import pandas as pd
import pytest

from gridmind import gesl


@pytest.mark.parametrize("nested", [False, True])
def test_observed_archive_formats(tmp_path, nested):
    source = tmp_path / "downloads"
    source.mkdir()
    path = source / "sigId-123.zip"
    angle = np.arange(120) * .02
    angle[60:] += 3
    trace = pd.DataFrame({"Time": np.round(np.arange(120) / 30, 3), "P001.vp_a": angle}).to_csv(index=False)
    metadata = "ID, Data Source, Description, Device/site, Event Tags, Sensor\n123, PMU - Eastern Interconnection, Clock error, , Instrument::Timing::Positive Seq Voltage Angle, PMU,\n"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("sigId-123-Metadata.csv", metadata)
        if nested:
            payload = io.BytesIO()
            with zipfile.ZipFile(payload, "w") as inner:
                inner.writestr("EventEI0001.csv", trace)
            archive.writestr("sigId-123.zip", payload.getvalue())
        else:
            archive.writestr("sigId-123.csv", trace)
    review = tmp_path / "review.json"
    gesl.inspect(source, review)
    document = json.loads(review.read_text())
    item = document["candidates"][0]
    assert item["channel"] == "P001_vp_a" and item["center"] == 60
    output = tmp_path / "manifest.json"
    gesl.prepare(source, review, output)
    assert not json.loads(output.read_text())["records"]
    item.update(reviewed=True, parent_family_id="fixture-family", review_reason="Synthetic software test")
    gesl.save_json(review, document)
    gesl.prepare(source, review, output)
    record = json.loads(output.read_text())["records"][0]
    assert record["source_samples"] == [15, 105]
    assert len(pd.read_csv(tmp_path / record["csv"])) == 90


def test_steady_and_unknown_tags_are_unsupported():
    assert gesl.source_label("State::Steady State::Nonspecific Steady State") == "unsupported"
    assert gesl.source_label("Events::Other::Unknown") == "unsupported"
    assert gesl.source_label("State::Change State::Trip") == "physical"
