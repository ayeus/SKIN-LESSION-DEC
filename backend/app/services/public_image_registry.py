"""Registry provenance for genuine acquired image manifests, not image blobs."""

import hashlib
import json
import os
from uuid import uuid4
import pandas as pd
from sqlalchemy import select
from ..db import ROOT, Session, Dataset, Audit
from .tabular import profile


def register_manifest(path, modality, name, source, license, scope):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    frame = pd.read_csv(path)
    with Session() as session:
        row = session.scalar(
            select(Dataset).where(
                Dataset.sha256 == digest, Dataset.modality == modality
            )
        )
        if row is None:
            row = Dataset(
                id=str(uuid4()),
                name=name,
                modality=modality,
                source=source,
                license=license,
                sha256=digest,
                path=str(path),
                profile=profile(frame),
            )
            session.add(row)
            session.add(
                Audit(
                    id=str(uuid4()),
                    action="public_image_manifest_import",
                    resource_id=row.id,
                )
            )
        row.profile = {**row.profile, "research_scope": scope}
        session.commit()
        return {
            "id": row.id,
            "name": row.name,
            "modality": modality,
            "source": row.source,
            "license": row.license,
            "sha256": row.sha256,
        }


def register_lesion_manifest(metadata):
    if metadata.resolve() == (ROOT / "raw/isic2018-task3/metadata.csv").resolve():
        validation = json.loads((metadata.parent / "validation.json").read_text())
        if validation.get("missing_images") != 0:
            raise ValueError("Official image extraction has not been validated")
        source, license = validation["source"], validation["license"]
    else:
        source, license = (
            os.getenv("DERMA_LESION_SOURCE"),
            os.getenv("DERMA_LESION_LICENSE"),
        )
        if not source or not license:
            raise ValueError(
                "Custom comparison manifest needs explicit DERMA_LESION_SOURCE and DERMA_LESION_LICENSE"
            )
    return register_manifest(
        metadata,
        "lesion",
        "Configured lesion classification cohort",
        source,
        license,
        {
            "limitations": "Genuine configured image manifest. Lesion-only groups cannot establish patient independence; no external or skin-tone clinical validation is inferred."
        },
    )
