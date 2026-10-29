"""Chronological model selection/testing and explicitly dimensioned workload scenarios."""

import math
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from .tabular import clean_json

FEATURES = [
    "previous_day",
    "previous_week",
    "previous_7_day_mean",
    "weekday_sin",
    "weekday_cos",
]
NAMES = ("last_value", "weekly_seasonal", "rolling_mean", "autoregressive_ridge")


def feature(history, date):
    angle = 2 * np.pi * date.dayofweek / 7
    return [
        history[-1],
        history[-7],
        float(np.mean(history[-7:])),
        float(np.sin(angle)),
        float(np.cos(angle)),
    ]


def fit_ridge(y, dates):
    x = np.asarray([feature(y[:i], dates[i]) for i in range(7, len(y))])
    return make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(x, y[7:])


def estimate(name, history, date, model=None):
    if name == "last_value":
        value = history[-1]
    elif name == "weekly_seasonal":
        value = history[-7]
    elif name == "rolling_mean":
        value = np.mean(history[-7:])
    else:
        value = model.predict(np.asarray([feature(history, date)]))[0]
    return max(0.0, float(value))


def errors(truth, predictions):
    return {
        "mae": float(mean_absolute_error(truth, predictions)),
        "rmse": float(np.sqrt(mean_squared_error(truth, predictions))),
    }


def capacity_scenario(future, p):
    raw = p.get("patients_per_staff_per_shift")
    if raw is None:
        if (
            p.get("shift_arrival_fractions") is not None
            or p.get("shift_hours") is not None
        ):
            raise ValueError(
                "Shift allocation needs explicit patients_per_staff_per_shift"
            )
        return None
    capacity = float(raw)
    if not np.isfinite(capacity) or capacity <= 0:
        raise ValueError("Capacity assumption must be finite and positive")
    result = {
        "assumption_patients_per_staff_per_shift": capacity,
        "required_staff_shifts_per_day": [
            math.ceil(float(v) / capacity) for v in future
        ],
        "label": "User-assumed workload equivalents, not observed staffing or a staffing prescription.",
        "limitations": "No skill mix, queueing, breaks, occupancy, minimum coverage, overtime or institutional safety policy is modeled.",
    }
    fractions = p.get("shift_arrival_fractions")
    if fractions is None and p.get("shift_hours") is not None:
        raise ValueError(
            "Shift hours require explicit arrival fractions; no allocation is inferred"
        )
    if fractions is not None:
        fractions = np.asarray(fractions, dtype=float)
        if (
            fractions.ndim != 1
            or not 1 <= len(fractions) <= 24
            or not np.isfinite(fractions).all()
            or (fractions < 0).any()
            or not np.isclose(fractions.sum(), 1, atol=1e-8, rtol=0)
        ):
            raise ValueError(
                "Provide 1–24 finite nonnegative shift arrival fractions summing to one"
            )
        hours = float(p.get("shift_hours", 0))
        if not np.isfinite(hours) or not 0 < hours <= 24:
            raise ValueError(
                "Explicit shift_hours in (0,24] required for shift staffing scenarios"
            )
        if len(fractions) * hours > 24:
            raise ValueError(
                "This simple non-overlapping shift scenario cannot exceed 24 hours per day"
            )
        result.update(
            assumed_shift_hours=hours,
            assumed_coverage_hours_per_day=len(fractions) * hours,
            assumed_arrival_fractions=fractions.tolist(),
            per_shift=[
                {
                    "day_index": i,
                    "shifts": [
                        {
                            "shift_index": j,
                            "expected_arrivals": float(value) * float(fraction),
                            "staff_required_under_assumptions": math.ceil(
                                float(value) * float(fraction) / capacity
                            ),
                        }
                        for j, fraction in enumerate(fractions)
                    ],
                }
                for i, value in enumerate(future)
            ],
        )
    else:
        result["allocation_status"] = (
            "Per-shift headcount unavailable: supply shift_arrival_fractions and shift_hours. Daily counts alone do not define shift arrivals."
        )
    return result


def forecast(df, p):
    date = p.get("date_column", "date")
    count = p.get("count_column", "count")
    if date not in df or count not in df:
        raise ValueError("Map date_column and count_column to observed daily data")
    dates = pd.to_datetime(
        df[date], format=p.get("date_format", "%Y-%m-%d"), errors="raise"
    )
    values = pd.to_numeric(df[count], errors="raise")
    if (
        dates.isna().any()
        or values.isna().any()
        or not np.isfinite(values).all()
        or (values < 0).any()
    ):
        raise ValueError("Dates/counts must be present; counts finite and nonnegative")
    if not np.equal(values, np.floor(values)).all():
        raise ValueError(
            "Observed patient counts must be whole numbers, not rates or averages"
        )
    if not (dates == dates.dt.normalize()).all():
        raise ValueError("Daily observations must use dates without times")
    ordered = pd.Series(values.to_numpy(), index=dates).sort_index()
    if ordered.index.duplicated().any():
        raise ValueError(
            "Duplicate daily dates: aggregate with documented policy first"
        )
    if len(ordered) < 28:
        raise ValueError(
            "At least 28 complete daily observations required for chronological train/validation/test"
        )
    if not ordered.index.equals(
        pd.date_range(ordered.index.min(), ordered.index.max(), freq="D")
    ):
        raise ValueError(
            "Missing days; do not silently interpret missing observations as zero"
        )
    days = float(p.get("horizon", 7))
    if not np.isfinite(days) or not days.is_integer() or not 1 <= days <= 90:
        raise ValueError("horizon must be a whole number from 1 through 90")
    horizon = int(days)
    y = ordered.to_numpy(dtype=float)
    dates = ordered.index
    train_end = min(len(y) - 14, max(14, int(len(y) * 0.6)))
    validation_end = min(len(y) - 7, max(train_end + 7, int(len(y) * 0.8)))
    model_validation = fit_ridge(y[:train_end], dates[:train_end])
    predictions = {
        name: np.asarray(
            [
                estimate(name, y[:i], dates[i], model_validation)
                for i in range(train_end, validation_end)
            ]
        )
        for name in NAMES
    }
    validation_scores = {
        name: errors(y[train_end:validation_end], v) for name, v in predictions.items()
    }
    selected = min(NAMES, key=lambda name: validation_scores[name]["mae"])
    # Selection is frozen before fitting on train+validation or examining test outcomes.
    model_test = (
        fit_ridge(y[:validation_end], dates[:validation_end])
        if selected == "autoregressive_ridge"
        else None
    )
    test_prediction = np.asarray(
        [
            estimate(selected, y[:i], dates[i], model_test)
            for i in range(validation_end, len(y))
        ]
    )
    radius = float(
        np.quantile(np.abs(y[train_end:validation_end] - predictions[selected]), 0.9)
    )
    model_final = fit_ridge(y, dates) if selected == "autoregressive_ridge" else None
    dates_future = pd.date_range(
        dates[-1] + pd.Timedelta(days=1), periods=horizon, freq="D"
    )
    history = list(y)
    future = []
    for day in dates_future:
        value = estimate(selected, history, day, model_final)
        future.append(value)
        history.append(value)
    result = {
        "protocol_version": "chronological-3split-v2",
        "selected": selected,
        "selection_criterion": "Validation MAE only; test outcomes never choose the model.",
        "validation_metrics": validation_scores,
        "test_metrics": errors(y[validation_end:], test_prediction),
        "validation_protocol": "Chronological train/validation/test. Candidate ridge parameters/scaling fit on training only. Selected model refit on train+validation for rolling one-step test; actual prior observations may be used, never the current/future target. Final model refit on all observations for recursive future forecasts.",
        "split": {
            "training_rows": train_end,
            "validation_rows": validation_end - train_end,
            "test_rows": len(y) - validation_end,
            "training_end": dates[train_end - 1].isoformat(),
            "validation_start": dates[train_end].isoformat(),
            "validation_end": dates[validation_end - 1].isoformat(),
            "test_start": dates[validation_end].isoformat(),
            "test_end": dates[-1].isoformat(),
        },
        "observed": [
            {"date": d.isoformat(), "count": float(v)} for d, v in ordered.items()
        ],
        "validation_predictions": [
            {
                "date": dates[i].isoformat(),
                "observed": float(y[i]),
                "predicted": float(predictions[selected][i - train_end]),
            }
            for i in range(train_end, validation_end)
        ],
        "test_predictions": [
            {
                "date": dates[i].isoformat(),
                "observed": float(y[i]),
                "predicted": float(test_prediction[i - validation_end]),
            }
            for i in range(validation_end, len(y))
        ],
        "forecast": [
            {
                "date": d.isoformat(),
                "count": v,
                "lower": max(0, v - radius),
                "upper": v + radius,
            }
            for d, v in zip(dates_future, future)
        ],
        "uncertainty": "Empirical 90th-percentile selected-validation absolute residual band. Not a calibrated multi-step prediction interval; selection and structural changes can affect coverage.",
        "test_empirical_band_coverage": float(
            np.mean(np.abs(y[validation_end:] - test_prediction) <= radius)
        ),
        "weekday_means": ordered.groupby(ordered.index.dayofweek).mean().to_dict(),
        "ridge_configuration": {
            "alpha": 1.0,
            "features": FEATURES,
            "nonnegative_prediction_clip": True,
        },
        "limitation": "Research demand forecasting only. Historical definitions, missing observations, reporting changes and target-population relevance require review. No hospital-specific staffing policy is inferred.",
    }
    if model_final is not None:
        result["selected_ridge_parameters"] = {
            "coefficients_standardized": model_final[-1].coef_.tolist(),
            "intercept": float(model_final[-1].intercept_),
            "feature_means": model_final[0].mean_.tolist(),
            "feature_scales": model_final[0].scale_.tolist(),
        }
    scenario = capacity_scenario(future, p)
    if scenario is not None:
        result["scenario"] = scenario
    return clean_json(result)
