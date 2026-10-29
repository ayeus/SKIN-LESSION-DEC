"""Official public England COVID-admissions case study, not a hospital arrival census."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
import pandas as pd
import numpy as np
from sqlalchemy import select
from scripts.acquire_public_data import acquire
from backend.app.db import ROOT, Session, Dataset, Audit
from backend.app.main import execute
from backend.app.services.forecasting import forecast, errors
from backend.app.services.tabular import profile

METRIC = "COVID-19_healthcare_admissionByDay"
SOURCE = "https://ukhsa-dashboard.data.gov.uk/respiratory-viruses/covid-19"
LICENSE = "Contains public sector information licensed under the Open Government Licence v3.0; UKHSA/NHS England attribution; no endorsement"


def prepare(rows, start, end):
    frame = pd.DataFrame(rows)
    required = {
        "date",
        "metric_value",
        "metric",
        "geography",
        "geography_type",
        "age",
        "sex",
        "stratum",
        "in_reporting_delay_period",
    }
    if not required <= set(frame):
        raise ValueError("Public API response does not match documented metric schema")
    expected = {
        "metric": METRIC,
        "geography": "England",
        "geography_type": "Nation",
        "age": "all",
        "sex": "all",
        "stratum": "default",
    }
    if any(not frame[key].eq(value).all() for key, value in expected.items()):
        raise ValueError(
            "Mixed metric/geography/age/sex/stratum cannot be silently aggregated"
        )
    dates = pd.to_datetime(frame.date, format="%Y-%m-%d", errors="raise")
    if dates.duplicated().any():
        raise ValueError("Repeated dates require source review; no automatic summing")
    counts = pd.to_numeric(frame.metric_value, errors="raise")
    if (
        counts.isna().any()
        or not np.isfinite(counts).all()
        or (counts < 0).any()
        or not (counts == counts.round()).all()
    ):
        raise ValueError("Observed admissions must be genuine finite whole counts")
    raw_dates = pd.DatetimeIndex(dates)
    missing_full = (
        pd.date_range(raw_dates.min(), raw_dates.max())
        .difference(raw_dates)
        .strftime("%Y-%m-%d")
        .tolist()
    )
    subset = frame.loc[dates.between(pd.Timestamp(start), pd.Timestamp(end))].copy()
    if subset.empty:
        raise ValueError("Requested historical case-study window has no observations")
    if subset.in_reporting_delay_period.any():
        raise ValueError(
            "Selected window includes reporting-delay observations; review before use"
        )
    selected = pd.DataFrame(
        {
            "date": pd.to_datetime(subset.date, format="%Y-%m-%d"),
            "count": pd.to_numeric(subset.metric_value),
        }
    ).sort_values("date")
    expected_dates = pd.date_range(start, end, freq="D")
    if not pd.DatetimeIndex(selected.date).equals(expected_dates):
        raise ValueError(
            "Case-study window has missing observations; no zero fill or invented arrivals permitted"
        )
    selected["date"] = selected.date.dt.strftime("%Y-%m-%d")
    selected["count"] = selected["count"].astype("int64")
    return selected, {
        "source_rows": len(frame),
        "selected_rows": len(selected),
        "requested_start": start,
        "requested_end": end,
        "missing_days_within_full_observed_range": missing_full,
        "selection_reason": "The initial January–May window was rejected before modeling because May 30/31 are absent. A complete January–April input window reserves May 1–7 for a retrospective recursive forecast check and avoids the June collection-change boundary. Window chosen before model evaluation; gaps are reported, never zero-filled.",
    }


def run(year=2023, start="2023-01-01", end="2023-04-30"):
    root = ROOT / "raw/ukhsa-covid-admissions" / str(year)
    base = f"https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/respiratory/topics/COVID-19/geography_types/Nation/geographies/England/metrics/{METRIC}"
    url = (
        base + f"?format=json&page_size=365&year={year}&sex=all&age=all&stratum=default"
    )
    rows = []
    page = 0
    while url:
        if (
            urlparse(url).scheme != "https"
            or urlparse(url).netloc != "api.ukhsa-dashboard.data.gov.uk"
        ):
            raise ValueError("Unexpected pagination host")
        page += 1
        if page > 20:
            raise ValueError("Acquisition pagination limit reached")
        path = acquire(url, root / f"page-{page:03d}.json", LICENSE, SOURCE)
        body = json.loads(path.read_text())
        rows.extend(body["results"])
        url = body["next"]
    frame, quality = prepare(rows, start, end)
    output = ROOT / "processed/public/ukhsa"
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"covid_admissions_england_{start}_{end}.csv"
    frame.to_csv(path, index=False)
    quality.update(
        source=SOURCE,
        metric=METRIC,
        license=LICENSE,
        metric_documentation="https://ukhsa-dashboard.data.gov.uk/metrics-documentation/covid-19-healthcare-admission-by-day",
        api_documentation="https://ukhsa-dashboard.data.gov.uk/access-our-data/getting-started",
        limitations="Publisher-reported COVID admissions in England, not all ED arrivals, an individual hospital, dermatology demand, or local staffing observations. Definitions/testing/reporting change over time; management-information limitations apply. Historical forecast dates are not current operational advice.",
    )
    (output / f"source-quality_{start}_{end}.json").write_text(
        json.dumps(quality, indent=2)
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with Session() as session:
        row = session.scalar(select(Dataset).where(Dataset.sha256 == digest))
        if row is None:
            row = Dataset(
                id=str(uuid4()),
                name=f"UKHSA England COVID admissions: {start} to {end}",
                modality="demand",
                source=SOURCE,
                license=LICENSE,
                sha256=digest,
                path=str(path),
                profile=profile(frame),
            )
            session.add(row)
            session.add(
                Audit(
                    id=str(uuid4()), action="public_dataset_import", resource_id=row.id
                )
            )
        row.profile = {**row.profile, "research_scope": quality}
        session.commit()
        id = row.id
    params = {"date_column": "date", "count_column": "count", "horizon": 7}

    def work(run_id):
        result = forecast(frame, params)
        result["data_scope"] = quality
        result["dataset_provenance"] = {
            "id": id,
            "name": row.name,
            "source": SOURCE,
            "license": LICENSE,
            "sha256": digest,
            "modality": "demand",
        }
        actual = {r["date"]: r["metric_value"] for r in rows}
        horizon_rows = [
            {
                "date": v["date"][:10],
                "observed": actual.get(v["date"][:10]),
                "predicted": v["count"],
            }
            for v in result["forecast"]
        ]
        if all(v["observed"] is not None for v in horizon_rows):
            result["retrospective_horizon_test"] = {
                "protocol": "Seven-day recursive forecast from the input cutoff, compared only after prediction with unused later observations from the same published source. Not an external-hospital validation.",
                "rows": horizon_rows,
                "metrics": errors(
                    [v["observed"] for v in horizon_rows],
                    [v["predicted"] for v in horizon_rows],
                ),
            }
            pd.DataFrame(horizon_rows).to_csv(
                output / f"horizon_holdout_{start}_{end}.csv", index=False
            )
        else:
            result["retrospective_horizon_test"] = {
                "status": "NOT VERIFIED",
                "reason": "Future observed days are incomplete; no outcome invented",
            }
        return result

    run = execute("forecast", params, work, id)
    report = {
        "dataset_id": id,
        "run_id": run["id"],
        "source_quality": quality,
        "selected": run["result"]["selected"],
        "split": run["result"]["split"],
        "validation_metrics": run["result"]["validation_metrics"],
        "test_metrics": run["result"]["test_metrics"],
        "staffing_scenario_generated": False,
        "retrospective_horizon_test": run["result"]["retrospective_horizon_test"],
    }
    (output / f"verification_{start}_{end}.json").write_text(
        json.dumps(report, indent=2)
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2023-04-30")
    args = parser.parse_args()
    run(args.year, args.start, args.end)
