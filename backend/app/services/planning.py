"""Explicit workload/coverage scenario comparisons; never observed staffing facts."""

import math
import numpy as np
from .forecasting import forecast, capacity_scenario


def integer_vector(value, length, name):
    vector = np.asarray(value, dtype=float)
    if (
        vector.ndim != 1
        or len(vector) != length
        or not np.isfinite(vector).all()
        or (vector < 0).any()
        or not (vector == np.floor(vector)).all()
    ):
        raise ValueError(
            f"{name} needs one nonnegative whole number per explicitly allocated shift"
        )
    return vector.astype(int)


def compare_scenarios(future, configurations):
    if not isinstance(configurations, list) or not 1 <= len(configurations) <= 10:
        raise ValueError("Provide 1–10 explicit named planning scenarios")
    names = set()
    results = []
    for configuration in configurations:
        if not isinstance(configuration, dict):
            raise ValueError("Each scenario must be an object of explicit assumptions")
        allowed = {
            "name",
            "patients_per_staff_per_shift",
            "shift_arrival_fractions",
            "shift_hours",
            "available_staff_per_shift",
            "minimum_staff_per_shift",
        }
        if set(configuration) - allowed:
            raise ValueError(
                "Unknown planning assumption fields; use documented scenario keys"
            )
        if not isinstance(configuration.get("name"), str):
            raise ValueError("Each scenario needs an explicit name")
        name = configuration["name"].strip()
        if not name or len(name) > 100 or name in names:
            raise ValueError(
                "Each scenario needs a unique name of at most 100 characters"
            )
        names.add(name)
        scenario = capacity_scenario(future, configuration)
        if scenario is None:
            raise ValueError("Every scenario requires patients_per_staff_per_shift")
        scenario = {"name": name, **scenario}
        available = configuration.get("available_staff_per_shift")
        minimum = configuration.get("minimum_staff_per_shift")
        if available is not None or minimum is not None:
            fractions = scenario.get("assumed_arrival_fractions")
            if fractions is None:
                raise ValueError(
                    "Available staff and minimum coverage need explicit shift fractions/hours"
                )
            n = len(fractions)
            coverage = (
                integer_vector(minimum, n, "minimum_staff_per_shift")
                if minimum is not None
                else None
            )
            capacity = float(configuration["patients_per_staff_per_shift"])
            staff = (
                integer_vector(available, n, "available_staff_per_shift")
                if available is not None
                else None
            )
            for day in scenario["per_shift"]:
                for shift in day["shifts"]:
                    j = shift["shift_index"]
                    need = (
                        max(shift["staff_required_under_assumptions"], int(coverage[j]))
                        if coverage is not None
                        else shift["staff_required_under_assumptions"]
                    )
                    shift["minimum_coverage_assumption"] = (
                        int(coverage[j]) if coverage is not None else None
                    )
                    shift["staff_required_including_coverage"] = need
                    if staff is not None:
                        slots = int(staff[j]) * capacity
                        shift.update(
                            available_staff_assumption=int(staff[j]),
                            assumed_patient_capacity=slots,
                            forecast_demand_to_assumed_capacity_ratio=shift[
                                "expected_arrivals"
                            ]
                            / slots
                            if slots
                            else None,
                            capacity_ratio_status="defined"
                            if slots
                            else "undefined: no assumed capacity",
                            workload_shortfall_staff=max(0, need - int(staff[j])),
                            expected_count_exceeding_assumed_capacity=max(
                                0.0, shift["expected_arrivals"] - slots
                            ),
                        )
            if coverage is not None:
                scenario["minimum_staff_per_shift_assumption"] = coverage.tolist()
            else:
                scenario["minimum_coverage_status"] = (
                    "Not supplied; no minimum-coverage policy inferred"
                )
            if staff is not None:
                scenario["available_staff_per_shift_assumption"] = staff.tolist()
        scenario["summary"] = {
            "peak_daily_workload_staff_shifts": max(
                scenario["required_staff_shifts_per_day"]
            ),
            "maximum_shift_workload_shortfall": max(
                (
                    shift["workload_shortfall_staff"]
                    for day in scenario.get("per_shift", [])
                    for shift in day["shifts"]
                    if "workload_shortfall_staff" in shift
                ),
                default=None,
            ),
        }
        scenario["interpretation"] = (
            "User assumptions applied to model forecasts; no observed utilization, staffing prescription, shift schedule, skill mix or institutional safety policy inferred."
        )
        results.append(scenario)
    return results


def plan(frame, parameters):
    # Forecast once so every scenario compares the same model-generated counts.
    result = forecast(frame, parameters)
    configurations = parameters.get("scenarios")
    if configurations is not None and not isinstance(configurations, list):
        raise ValueError("Planning scenarios must be a JSON array")
    if configurations:
        result["planning_scenarios"] = compare_scenarios(
            [row["count"] for row in result["forecast"]], configurations
        )
        result["planning_status"] = (
            "Explicit user scenarios calculated from the same forecast"
        )
    elif result.get("scenario"):
        result["planning_status"] = (
            "Single user-defined workload scenario; no multi-scenario assumptions supplied"
        )
    else:
        result["planning_status"] = (
            "Waiting for explicit staffing/capacity assumptions; forecasting evidence only"
        )
    result["planning_separation"] = {
        "observed": "Historical count rows only",
        "forecast": "Model-generated future counts, not observed outcomes",
        "scenario": "User-supplied capacity/coverage/staff values, not observed facts",
        "actions": "Operational decisions require institution-specific policy and human review",
    }
    return result
