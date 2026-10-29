"""Real MIMIC demo relationship/cleaning verification; no patient rows printed."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4
import pandas as pd
from sqlalchemy import select
from backend.app.db import Dataset, Session, ROOT, Audit
from backend.app.services.tabular import profile
from backend.app.main import execute


def verify():
    root = ROOT / "processed/public/mimic"
    patients = pd.read_csv(root / "patients.csv")
    admissions = pd.read_csv(root / "admissions.csv")
    diagnoses = pd.read_csv(root / "diagnoses_icd.csv", dtype={"icd_code": str})
    dictionary = pd.read_csv(root / "d_icd_diagnoses.csv", dtype={"icd_code": str})
    if patients.subject_id.duplicated().any():
        raise ValueError("Duplicate subject primary keys")
    if admissions.hadm_id.duplicated().any():
        raise ValueError("Duplicate encounter primary keys")
    if not set(admissions.subject_id) <= set(patients.subject_id):
        raise ValueError("Orphan encounters")
    if not set(diagnoses.hadm_id) <= set(admissions.hadm_id):
        raise ValueError("Orphan diagnoses")
    joined = diagnoses.merge(
        dictionary, on=["icd_code", "icd_version"], how="left", validate="many_to_one"
    )
    if joined.long_title.isna().any():
        raise ValueError("Unmapped diagnosis codes")
    path = root / "diagnoses_with_dictionary.csv"
    joined.to_csv(path, index=False)
    registered = {}
    with Session() as session:
        for name, frame in [
            ("patients", patients),
            ("admissions", admissions),
            ("diagnoses_with_dictionary", joined),
        ]:
            path = root / (name + ".csv")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            row = session.scalar(select(Dataset).where(Dataset.sha256 == digest))
            if row is None:
                row = Dataset(
                    id=str(uuid4()),
                    name="MIMIC-IV public demo 2.2: " + name,
                    modality="ehr",
                    source="https://physionet.org/content/mimic-iv-demo/2.2/",
                    license="Open Database License v1.0; Johnson et al. (2023), doi:10.13026/dp1f-ex47",
                    sha256=digest,
                    path=str(path),
                    profile=profile(frame),
                )
                session.add(row)
                session.add(
                    Audit(
                        id=str(uuid4()),
                        action="public_dataset_import",
                        resource_id=row.id,
                    )
                )
            registered[name] = row.id
        session.commit()
    from backend.app.services.tabular import transform

    def work(id):
        output, report = transform(
            admissions,
            {
                "types": {"admittime": "date", "dischtime": "date"},
                "date_formats": {
                    "admittime": "%Y-%m-%d %H:%M:%S",
                    "dischtime": "%Y-%m-%d %H:%M:%S",
                },
                "duplicate_keys": ["subject_id"],
                "drop_exact_duplicates": False,
            },
        )
        directory = ROOT / "processed" / id
        directory.mkdir(parents=True, exist_ok=True)
        output.to_csv(directory / "transformed.csv", index=False)
        return report

    run = execute(
        "preprocess",
        {"verification": "real public MIMIC-IV demo, explicit date standardization"},
        work,
        registered["admissions"],
    )
    report = {
        "source": "MIMIC-IV demo 2.2",
        "genuine_public_data": True,
        "patients": len(patients),
        "encounters": len(admissions),
        "diagnosis_rows": len(joined),
        "orphan_encounters": 0,
        "orphan_diagnoses": 0,
        "unmapped_diagnosis_codes": 0,
        "registered_datasets": registered,
        "transformation_run": run["id"],
        "status": "relationship and date standardization checks passed",
        "limits": "Small public subset, no clinical NLP notes, no actual hospital calendar demand, no clinical effectiveness claim.",
    }
    (root / "verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    verify()
