"""Documented 2017–2018 NHANES adult exploratory study; no population/causal claims."""

import hashlib
import json
from uuid import uuid4
import pandas as pd
from sqlalchemy import select
from backend.app.db import ROOT, Session, Dataset, Audit
from backend.app.services.tabular import profile
from backend.app.services.analytics import research
from backend.app.main import execute


def prepare(frame):
    # Definitions read from official 2017 component manuals retained alongside XPT files.
    adults = frame.loc[frame.RIDAGEYR >= 20].copy()
    out = pd.DataFrame(
        {
            "participant_id": adults.SEQN,
            "age_years_topcoded80": adults.RIDAGEYR,
            "female_reported": adults.RIAGENDR.map({1: 0, 2: 1}),
            "bmi_kg_m2": adults.BMXBMI,
            "sedentary_minutes_day": adults.PAD680.where(
                adults.PAD680.between(0, 1320)
            ),
            "sleep_weekday_hours_exact": adults.SLD012.where(
                adults.SLD012.between(3, 13.5)
            ),
            "meals_away_week_exact": adults.DBD895.where(adults.DBD895.between(0, 21)),
            "mec_weight": adults.WTMEC2YR,
            "survey_psu": adults.SDMVPSU,
            "survey_stratum": adults.SDMVSTRA,
        }
    )
    log = {
        "adult_inclusion": "RIDAGEYR >= 20; age 80 represents 80+",
        "PAD680": "0–1320 observed minute range; 7777 refused/9999 unknown -> missing",
        "SLD012": "Exact range 3–13.5 hours retained; code 2 (<3h) and 14 (>=14h) -> missing for exact-hours analysis; not interpreted as exact values",
        "DBD895": "0–21 observed meals retained; 5555 (>21),7777 refusal,9999 unknown -> missing; no structural missing value filled with zero",
        "RIAGENDR": "Source 1 male->0,2 female->1; survey field only, no inferred identity",
        "outcome": "Measured BMXBMI. Weight and height excluded from predictors to avoid algebraic target leakage.",
        "survey": "Weights/PSU/strata retained but not applied by current regression. Unweighted exploratory associations only.",
    }
    return out, log


def verify():
    root = ROOT / "processed/public/nhanes"
    raw = pd.read_csv(root / "adults_raw_codes.csv")
    frame, log = prepare(raw)
    path = root / "adults_exploratory.csv"
    frame.to_csv(path, index=False)
    (root / "transformation-definition.json").write_text(json.dumps(log, indent=2))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with Session() as s:
        row = s.scalar(select(Dataset).where(Dataset.sha256 == digest))
        if row is None:
            row = Dataset(
                id=str(uuid4()),
                name="NHANES 2017–2018 adults: documented exploratory fields",
                modality="weight",
                source="https://wwwn.cdc.gov/Nchs/Nhanes/Search/DataPage.aspx?Cycle=2017-2018",
                license="CDC/NCHS public-use statistical analysis only; no re-identification; cite NHANES 2017–2018",
                sha256=digest,
                path=str(path),
                profile=profile(frame),
            )
            s.add(row)
            s.add(
                Audit(
                    id=str(uuid4()), action="public_dataset_import", resource_id=row.id
                )
            )
        s.commit()
        id = row.id
    params = {
        "features": [
            "age_years_topcoded80",
            "female_reported",
            "sedentary_minutes_day",
            "sleep_weekday_hours_exact",
            "meals_away_week_exact",
        ],
        "target": "bmi_kg_m2",
        "group_column": "participant_id",
    }
    run = execute("research", params, lambda run_id: research(frame, params), id)
    result = run["result"]
    summary = {
        "dataset_id": id,
        "adult_rows": len(frame),
        "train_rows": result["train_rows"],
        "test_rows": result["test_rows"],
        "run_id": run["id"],
        "metrics": {k: result[k] for k in ["mae", "rmse", "r2"]},
        "transformations": log,
        "status": "real-data pipeline executed; no causal or US-population inference, no clinical effectiveness claim",
    }
    (root / "verification.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    verify()
