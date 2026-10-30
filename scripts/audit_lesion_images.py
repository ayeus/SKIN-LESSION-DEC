"""Run after complete acquisition/extraction; inspect actual image content and leakage."""

import json
import pandas as pd
from backend.app import training
from backend.app.services.image_audit import audit_images
from backend.app.services.ml import split_metadata

if __name__ == "__main__":
    metadata, images = training.source_paths()
    frame = pd.read_csv(metadata, dtype={"label": str, "group_id": str})
    split_metadata(frame)
    report = audit_images(frame, images)
    path = metadata.parent / "content-audit.json"
    path.write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k
                not in [
                    "image_records",
                    "cross_group_encoded_duplicates",
                    "cross_group_decoded_duplicates",
                    "invalid_images",
                ]
            },
            indent=2,
        )
    )
    if not report["ready"]:
        raise SystemExit(
            "Content audit failed; inspect saved error/duplicate records. No training authorized on these unresolved inputs."
        )
