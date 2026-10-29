"""Isolated source-contract fixtures, never application observations."""

import json
import hashlib
import pandas as pd
import pytest
from scripts.acquire_public_demand import prepare, METRIC
from scripts import acquire_public_data as acquisition


def rows():
    return [
        {
            "date": d.strftime("%Y-%m-%d"),
            "metric_value": i,
            "metric": METRIC,
            "geography": "England",
            "geography_type": "Nation",
            "age": "all",
            "sex": "all",
            "stratum": "default",
            "in_reporting_delay_period": False,
        }
        for i, d in enumerate(pd.date_range("2023-01-01", periods=3))
    ]


def test_public_source_missing_days_are_not_zero_filled():
    source = rows()
    source.pop(1)
    with pytest.raises(ValueError, match="missing observations"):
        prepare(source, "2023-01-01", "2023-01-03")


def test_public_source_scope_and_counts_are_explicit():
    frame, report = prepare(rows(), "2023-01-01", "2023-01-03")
    assert frame["count"].tolist() == [0, 1, 2]
    source = rows()
    source[0]["geography"] = "Other location"
    with pytest.raises(ValueError, match="Mixed"):
        prepare(source, "2023-01-01", "2023-01-03")
    source = rows()
    source[0]["in_reporting_delay_period"] = True
    with pytest.raises(ValueError, match="reporting-delay"):
        prepare(source, "2023-01-01", "2023-01-03")


def test_raw_cache_cannot_be_relabelled_or_tampered(tmp_path, monkeypatch):
    monkeypatch.setattr(acquisition, "ROOT", tmp_path)
    path = tmp_path / "raw/source.json"
    path.parent.mkdir()
    path.write_bytes(b"isolated fixture")
    receipt = path.with_suffix(".json.provenance.json")
    receipt.write_text(
        json.dumps(
            {
                "url": "https://example.test/original",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    )
    with pytest.raises(ValueError, match="different source URL"):
        acquisition.acquire(
            "https://example.test/other", path, "test license", "test source"
        )
    path.write_bytes(b"changed fixture")
    with pytest.raises(ValueError, match="changed since acquisition"):
        acquisition.acquire(
            "https://example.test/original", path, "test license", "test source"
        )
