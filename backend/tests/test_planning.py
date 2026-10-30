"""Synthetic workload arithmetic; never hospital staffing recommendations."""

import pytest
from backend.app.services.planning import compare_scenarios


def test_capacity_coverage_and_zero_capacity_are_distinguished():
    configs = [
        {
            "name": "explicit unit fixture",
            "patients_per_staff_per_shift": 5,
            "shift_arrival_fractions": [0.5, 0.5],
            "shift_hours": 8,
            "available_staff_per_shift": [1, 0],
            "minimum_staff_per_shift": [2, 1],
        }
    ]
    result = compare_scenarios([20.0], configs)[0]
    a, b = result["per_shift"][0]["shifts"]
    assert (
        a["staff_required_including_coverage"] == 2
        and a["forecast_demand_to_assumed_capacity_ratio"] == 2
    )
    assert a["workload_shortfall_staff"] == 1
    assert (
        b["forecast_demand_to_assumed_capacity_ratio"] is None
        and b["workload_shortfall_staff"] == 2
    )
    assert b["expected_count_exceeding_assumed_capacity"] == 10
    assert result["summary"]["peak_daily_workload_staff_shifts"] == 4


@pytest.mark.parametrize(
    "change",
    [
        {"minimum_staff_per_shift": [1]},
        {"available_staff_per_shift": [1.2, 2]},
        {"available_staff_per_shift": [-1, 2]},
    ],
)
def test_misaligned_or_fractional_staffing_is_rejected(change):
    config = {
        "name": "test only",
        "patients_per_staff_per_shift": 4,
        "shift_arrival_fractions": [0.5, 0.5],
        "shift_hours": 8,
        **change,
    }
    with pytest.raises(ValueError):
        compare_scenarios([20.0], [config])


def test_scenarios_use_same_forecast_but_distinct_explicit_capacity_assumptions():
    result = compare_scenarios(
        [20.0, 30.0],
        [
            {"name": "a", "patients_per_staff_per_shift": 5},
            {"name": "b", "patients_per_staff_per_shift": 10},
        ],
    )
    assert result[0]["required_staff_shifts_per_day"] == [4, 6]
    assert result[1]["required_staff_shifts_per_day"] == [2, 3]
    assert result[0]["summary"]["maximum_shift_workload_shortfall"] is None
