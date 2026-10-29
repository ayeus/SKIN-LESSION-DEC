"""Synthetic mathematical series only; not healthcare forecasting results."""

import numpy as np
import pandas as pd
import pytest
from backend.app.services.forecasting import forecast, capacity_scenario


def series(n=70):
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=n).strftime("%Y-%m-%d"),
            "count": np.tile([4, 8, 12, 16, 20, 24, 28], n // 7 + 1)[:n],
        }
    )


def test_temporal_boundaries_and_selected_test_predictions_are_disjoint():
    r = forecast(series(28), {})
    assert [
        r["split"][k] for k in ["training_rows", "validation_rows", "test_rows"]
    ] == [14, 7, 7]
    assert (
        r["split"]["training_end"]
        < r["split"]["validation_start"]
        <= r["split"]["validation_end"]
        < r["split"]["test_start"]
    )
    assert len(r["test_predictions"]) == 7 and r["test_metrics"] == {
        "mae": 0.0,
        "rmse": 0.0,
    }
    assert r["selected"] == min(
        r["validation_metrics"], key=lambda k: r["validation_metrics"][k]["mae"]
    )
    assert "autoregressive_ridge" in r["validation_metrics"]


def test_test_outcomes_cannot_change_model_selection_or_validation():
    a = series()
    b = a.copy()
    b.loc[56:, "count"] += 1000
    ra, rb = forecast(a, {}), forecast(b, {})
    assert (
        ra["validation_metrics"] == rb["validation_metrics"]
        and ra["selected"] == rb["selected"]
    )
    assert ra["test_metrics"] != rb["test_metrics"]
    assert (
        ra["test_predictions"][0]["predicted"] == rb["test_predictions"][0]["predicted"]
    )


def test_staff_shift_units_require_explicit_allocation_before_headcounts():
    r = forecast(series(), {"patients_per_staff_per_shift": 4})
    assert "staff_per_shift" not in r["scenario"] and "per_shift" not in r["scenario"]
    assert r["scenario"]["required_staff_shifts_per_day"] == [1, 2, 3, 4, 5, 6, 7]
    s = forecast(
        series(),
        {
            "patients_per_staff_per_shift": 4,
            "shift_arrival_fractions": [0.5, 0.5],
            "shift_hours": 8,
        },
    )["scenario"]
    assert s["assumed_coverage_hours_per_day"] == 16
    assert [v["expected_arrivals"] for v in s["per_shift"][0]["shifts"]] == [2, 2]
    assert [
        v["staff_required_under_assumptions"] for v in s["per_shift"][0]["shifts"]
    ] == [1, 1]


@pytest.mark.parametrize(
    "parameters",
    [
        {"patients_per_staff_per_shift": 4, "shift_hours": 8},
        {"patients_per_staff_per_shift": 0},
        {"patients_per_staff_per_shift": float("nan")},
        {"patients_per_staff_per_shift": 4, "shift_arrival_fractions": [0.5, 0.5]},
        {
            "patients_per_staff_per_shift": 4,
            "shift_arrival_fractions": [0.7, 0.7],
            "shift_hours": 8,
        },
        {
            "patients_per_staff_per_shift": 4,
            "shift_arrival_fractions": [0.5, 0.5],
            "shift_hours": 16,
        },
    ],
)
def test_invalid_scenario_assumptions_are_not_silently_used(parameters):
    with pytest.raises(ValueError):
        capacity_scenario([20.0], parameters)


def test_fractional_observed_counts_and_horizons_are_rejected():
    data = series()
    data["count"] = data["count"].astype(float)
    data.loc[0, "count"] = 4.5
    with pytest.raises(ValueError, match="whole numbers"):
        forecast(data, {})
    with pytest.raises(ValueError, match="whole number"):
        forecast(series(), {"horizon": 1.9})
