"""Real NHANES exploratory geometry; never cluster/clinical validity evidence."""

import hashlib
import json
import pandas as pd
from sqlalchemy import select
from backend.app.db import ROOT, Session, Dataset
from backend.app.main import execute
from backend.app.services.analytics import reduce

FEATURES = [
    "age_years_topcoded80",
    "female_reported",
    "sedentary_minutes_day",
    "sleep_weekday_hours_exact",
    "meals_away_week_exact",
]


def verify():
    path = ROOT / "processed/public/nhanes/adults_exploratory.csv"
    if not path.is_file():
        raise ValueError("Acquire NHANES and run verify_public_weight before reduction")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with Session() as session:
        row = session.scalar(
            select(Dataset).where(
                Dataset.sha256 == digest, Dataset.modality == "weight"
            )
        )
        if row is None:
            raise ValueError(
                "Derived source checksum is not registered; verify its provenance first"
            )
        provenance = {
            "id": row.id,
            "name": row.name,
            "source": row.source,
            "license": row.license,
            "modality": row.modality,
            "sha256": digest,
        }
    frame = pd.read_csv(path)
    summary = {
        "dataset_provenance": provenance,
        "rows": len(frame),
        "features": FEATURES,
        "limitation": "Unweighted descriptive geometry, not population estimates, clinical labels, predictive performance or causal evidence. Median imputation may alter neighborhood structure. Participants/modalities are not pooled.",
        "runs": [],
    }
    for method in ["pca", "tsne"]:
        parameters = {
            "features": FEATURES,
            "method": method,
            "dimensions": 3,
            "perplexity": 30,
        }

        def work(run_id):
            result = reduce(frame, parameters)
            result["dataset_provenance"] = provenance
            result["data_scope"] = {"limitations": summary["limitation"]}
            return result

        run = execute("reduce", parameters, work, provenance["id"])
        if run["status"] != "completed":
            raise RuntimeError(
                f"{method} run {run['id']} failed; inspect persisted run error"
            )
        result = run["result"]
        summary["runs"].append(
            {
                "id": run["id"],
                "method": method,
                "dimensions": result["dimensions"],
                "rows": result["rows"],
                **{
                    key: result[key]
                    for key in [
                        "explained_variance_ratio",
                        "perplexity",
                        "kl_divergence",
                        "iterations",
                        "seed",
                    ]
                    if key in result
                },
            }
        )
    (path.parent / "reduction-verification.json").write_text(
        json.dumps(summary, indent=2)
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    verify()
