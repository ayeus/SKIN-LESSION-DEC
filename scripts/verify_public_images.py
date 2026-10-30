"""Actual image-lab processing and same-lesion registration on acquired HAM images."""

import hashlib
import json
import pandas as pd
from backend.app import training
from backend.app.db import ROOT
from backend.app.main import execute
from backend.app.services.images import decode, process, register
from backend.app.services.public_image_registry import register_lesion_manifest


def verify():
    metadata, images = training.source_paths()
    frame = pd.read_csv(metadata)
    provenance = register_lesion_manifest(metadata)
    first = frame.iloc[0]
    raw = (images / first.image_path).read_bytes()
    rgb = decode(raw)
    runs = []
    for method, parameters in [
        ("contrast", {}),
        ("equalize", {}),
        ("clahe", {}),
        ("gamma", {"gamma": 1.2}),
        ("gray_world", {}),
        ("gaussian", {}),
        ("median", {}),
        ("bilateral", {}),
        ("denoise", {}),
        ("threshold", {"threshold": 128}),
        ("otsu", {}),
        ("morphology", {}),
        ("edges", {}),
        ("grabcut", {}),
        ("jpeg", {"quality": 80}),
        ("png", {}),
        ("webp", {"quality": 80}),
    ]:

        def work(identifier):
            result = process(rgb, method, parameters)
            result["dataset_provenance"] = provenance
            result["source_image_id"] = first.image_path
            result["input_sha256"] = hashlib.sha256(raw).hexdigest()
            return result

        run = execute(
            "image",
            {
                "method": method,
                "parameters": parameters,
                "source_image_id": first.image_path,
            },
            work,
            provenance["id"],
        )
        runs.append(
            {
                "id": run["id"],
                "method": method,
                "metrics": {
                    k: v for k, v in run["result"]["metrics"].items() if k != "download"
                },
            }
        )
    groups = frame.groupby("group_id").filter(lambda group: len(group) >= 2)
    pair = groups.loc[groups.group_id == groups.iloc[0].group_id].head(2)
    first_path, second_path = [images / value for value in pair.image_path]
    # One prospectively selected same-lesion pair; unsuitable structure remains a real failed run.
    try:
        registration = execute(
            "registration",
            {
                "source_image_ids": pair.image_path.tolist(),
                "pair_selection": "First available source lesion group with at least two images; no outcome-based pair search",
            },
            lambda identifier: {
                **register(
                    decode(first_path.read_bytes()), decode(second_path.read_bytes())
                ),
                "dataset_provenance": provenance,
            },
            provenance["id"],
        )
        registration_summary = {
            "id": registration["id"],
            "status": registration["status"],
            **{
                key: registration["result"][key]
                for key in [
                    "keypoints_first",
                    "keypoints_second",
                    "matches",
                    "inliers",
                    "outliers",
                    "homography",
                ]
                if key in registration["result"]
            },
        }
    except Exception as error:
        from fastapi import HTTPException

        cause = error.__cause__
        allowed = (
            "Insufficient SIFT descriptors",
            "Fewer than four valid correspondences",
            "No valid homography found",
        )
        if (
            not isinstance(error, HTTPException)
            or not isinstance(cause, ValueError)
            or not str(cause).startswith(allowed)
        ):
            raise
        registration_summary = {
            "status": "FAILED / UNSUITABLE PAIR",
            "exception": type(error).__name__,
            "reason": str(error),
            "limitation": "Failure is preserved in run history, not converted to a successful registration",
        }
    summary = {
        "dataset_provenance": provenance,
        "image_processing_runs": runs,
        "registration": registration_summary,
        "limitation": "Actual permitted dataset images, not synthetic substitutions. Processing quality is not diagnostic benefit. Registration has no independently measured ground-truth transform or biological validity.",
    }
    output = ROOT / "processed/public/isic2018-image-lab"
    output.mkdir(parents=True, exist_ok=True)
    (output / "verification.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    verify()
