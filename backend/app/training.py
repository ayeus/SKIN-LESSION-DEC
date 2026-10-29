"""Server-controlled experiment paths; no arbitrary artifact upload or promotion."""

import json
import os
from pathlib import Path
from .db import ROOT


def source_paths():
    root = ROOT / "raw/isic2018-task3"
    return Path(os.getenv("DERMA_LESION_METADATA", str(root / "metadata.csv"))), Path(
        os.getenv("DERMA_LESION_IMAGES", str(root / "images"))
    )


def readiness():
    metadata, images = source_paths()
    if not metadata.is_file():
        return {"ready": False, "reason": "Labeled image metadata is not available"}
    import pandas as pd

    try:
        from .services.ml import split_metadata

        frame = pd.read_csv(metadata, dtype={"label": str, "group_id": str})
        split_metadata(frame)
        missing = 0
        for value in frame.image_path:
            path = (images / value).resolve()
            if not path.is_relative_to(images.resolve()):
                raise ValueError("Image path escapes configured dataset")
            missing += not path.is_file()
        return {
            "ready": missing == 0,
            "manifest_rows": len(frame),
            "missing_images": missing,
            "classes": sorted(frame.label.unique().tolist()),
            "reason": "All manifest files exist; full content/leakage checks occur before training"
            if not missing
            else "Image download/extraction is incomplete",
            "grouping_limit": "Group IDs must represent patients where available. Lesion-only groups cannot rule out same-patient leakage.",
        }
    except ImportError:
        return {
            "ready": False,
            "reason": "CNN runtime is unavailable; install backend/requirements-ml.txt or use the full locked environment",
        }
    except (ValueError, KeyError, OSError) as error:
        return {"ready": False, "reason": str(error)}


def artifact_dir(run_id):
    return ROOT / "models" / run_id


def selected_directory():
    configured = os.getenv("DERMA_MODEL_DIR")
    if configured:
        return Path(configured)
    pointer = ROOT / "model-selection.json"
    if not pointer.exists():
        return None
    try:
        id = json.loads(pointer.read_text())["training_run_id"]
        from uuid import UUID

        UUID(id)
        return artifact_dir(id)
    except (ValueError, KeyError):
        return None


def select_artifact(run_id):
    from .services.ml import load_artifact

    _, manifest = load_artifact(artifact_dir(run_id))
    path = ROOT / "model-selection.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {"training_run_id": run_id, "weights_sha256": manifest["weights_sha256"]}
        )
    )
    temporary.replace(path)
    return {
        "training_run_id": run_id,
        "weights_sha256": manifest["weights_sha256"],
        "research_only": True,
        "clinical_validation": "Not established",
    }


def acquisition_state():
    """Local byte/label measurements only; a partial file does not prove an active transfer."""
    root = ROOT / "raw/isic2018-task3"
    archive = root / "ISIC2018_Task3_Training_Input.zip"
    partial = archive.with_suffix(".zip.part")
    expected = None
    resource = root / "archive-resource.json"
    if resource.is_file():
        try:
            value = json.loads(resource.read_text()).get("expected_bytes")
            if isinstance(value, int) and 0 < value <= 12 * 1024**3:
                expected = value
        except (ValueError, OSError):
            pass
    received = (
        archive.stat().st_size
        if archive.is_file()
        else partial.stat().st_size
        if partial.is_file()
        else 0
    )
    result = {
        "state": "archive_present"
        if archive.is_file()
        else "partial_archive"
        if partial.is_file()
        else "not_downloaded",
        "bytes_on_disk": received,
        "expected_bytes": expected,
        "fraction_on_disk": received / expected
        if expected and received <= expected
        else None,
        "note": "Disk bytes do not establish transfer liveness, archive integrity, extraction completeness or a trained model.",
    }
    manifest = root / "metadata.csv"
    if manifest.is_file():
        import pandas as pd

        frame = pd.read_csv(manifest)
        if {"label", "group_id", "image_path"} <= set(frame):
            result.update(
                manifest_rows=len(frame),
                lesion_groups=int(frame.group_id.nunique()),
                class_distribution={
                    str(k): int(v) for k, v in frame.label.value_counts().items()
                },
            )
    return result
