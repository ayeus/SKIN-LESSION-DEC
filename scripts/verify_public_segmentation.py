"""Fixed classical segmentation benchmark on official ISIC2018 validation data.

All image/mask pairs, no parameter tuning, 512px maximum-side representation;
results are not the challenge's original-resolution model score or clinical validation.
"""

import io
import json
from pathlib import Path
from zipfile import ZipFile
import cv2
import numpy as np
from PIL import Image
from backend.app.db import ROOT
from backend.app.main import execute
from backend.app.services.images import process, mask_metrics


def members(archive, suffix):
    result = {}
    for item in archive.infolist():
        if (
            item.is_dir()
            or "__MACOSX" in item.filename
            or not item.filename.endswith(suffix)
        ):
            continue
        name = Path(item.filename).name
        if name in result or item.file_size > 30 * 1024**2:
            raise ValueError("Duplicate/oversized benchmark archive member")
        result[name] = item
    if not result:
        raise ValueError("No matching archive images/masks")
    return result


def evaluate_pairs(image_archive, mask_archive):
    rows = []
    counts = {}
    with ZipFile(image_archive) as images, ZipFile(mask_archive) as masks:
        image_files = members(images, ".jpg")
        mask_files = members(masks, "_segmentation.png")
        expected = {
            name.removesuffix("_segmentation.png") + ".jpg" for name in mask_files
        }
        if expected != set(image_files):
            raise ValueError("Source image/mask IDs are not one-to-one")
        if images.testzip() is not None or masks.testzip() is not None:
            raise ValueError("Source archive CRC mismatch")
        counts = {"images": len(image_files), "expert_masks": len(mask_files)}
        for name in sorted(image_files):
            key = Path(name).stem
            with Image.open(io.BytesIO(images.read(image_files[name]))) as source:
                if source.getexif().get(274) not in (None, 1):
                    raise ValueError(
                        "Image orientation requires explicit expert-mask alignment"
                    )
                rgb = np.asarray(source.convert("RGB"))
            with Image.open(
                io.BytesIO(masks.read(mask_files[key + "_segmentation.png"]))
            ) as reference:
                truth = np.asarray(reference.convert("L"))
            if truth.shape != rgb.shape[:2] or not set(np.unique(truth)) <= {0, 255}:
                raise ValueError("Ground truth must be matching binary expert mask")
            h, w = truth.shape
            factor = min(1, 512 / max(h, w))
            size = (max(8, round(w * factor)), max(8, round(h * factor)))
            rgb = cv2.resize(rgb, size, interpolation=cv2.INTER_AREA)
            truth = cv2.resize(truth, size, interpolation=cv2.INTER_NEAREST)
            for method in ["otsu", "morphology"]:
                result = process(rgb, method, {"kernel": 5})
                import base64

                with Image.open(
                    io.BytesIO(base64.b64decode(result["mask"].split(",")[1]))
                ) as mask:
                    predicted = np.asarray(mask.convert("L"))
                rows.append(
                    {
                        "source_image_id": key,
                        "method": method,
                        "original_width": w,
                        "original_height": h,
                        "evaluated_width": size[0],
                        "evaluated_height": size[1],
                        **mask_metrics(predicted, truth),
                    }
                )
    if not rows:
        raise ValueError("No actual paired evaluation performed")
    summary = {
        method: {
            metric: float(np.mean([r[metric] for r in rows if r["method"] == method]))
            for metric in ["dice", "iou"]
        }
        for method in ["otsu", "morphology"]
    }
    return {
        "source": "https://challenge.isic-archive.com/data/",
        "license": "CC0; cite Codella et al. ISIC2018",
        "source_partition": "official validation images/masks; no challenge test claim",
        "counts": counts,
        "protocol": {
            "methods": ["dark-foreground Otsu", "Otsu plus 5x5 morphological opening"],
            "max_side": 512,
            "image_interpolation": "area",
            "mask_interpolation": "nearest",
            "parameter_selection": "fixed before evaluation; no tuning on these annotations",
            "aggregation": "unweighted arithmetic mean of per-image Dice/IoU; empty/empty convention=1",
        },
        "mean_metrics": summary,
        "per_image": rows,
        "limitation": "Generic intensity baselines evaluated at reduced resolution. Not trained lesion segmentation, original-resolution challenge scores, patient-independent validation or demonstrated diagnostic utility.",
    }


def run_benchmark():
    import hashlib
    import pandas as pd
    from backend.app.services.public_image_registry import register_manifest

    root = ROOT / "raw/isic2018-task1-validation"
    images = root / "ISIC2018_Task1-2_Validation_Input.zip"
    masks = root / "ISIC2018_Task1_Validation_GroundTruth.zip"
    output = ROOT / "processed/public/isic2018-segmentation"
    output.mkdir(parents=True, exist_ok=True)
    with ZipFile(images) as image_archive, ZipFile(masks) as mask_archive:
        image_files = members(image_archive, ".jpg")
        mask_files = members(mask_archive, "_segmentation.png")
        records = [
            {
                "source_image_id": Path(name).stem,
                "image_archive_member": item.filename,
                "mask_archive_member": mask_files[
                    Path(name).stem + "_segmentation.png"
                ].filename,
            }
            for name, item in sorted(image_files.items())
        ]
    path = output / "paired_manifest.csv"
    pd.DataFrame(records).to_csv(path, index=False)
    source_hashes = {}
    for file in [images, masks]:
        with file.open("rb") as stream:
            source_hashes[file.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    provenance = register_manifest(
        path,
        "segmentation",
        "ISIC2018 Task1 official validation image/mask pairs",
        "https://challenge.isic-archive.com/data/",
        "CC0; cite Codella et al. ISIC2018",
        {
            "source_archive_sha256": source_hashes,
            "limitations": "Public expert-mask research benchmark; no original-resolution challenge/test or clinical validity claim.",
        },
    )

    def work(rid):
        result = evaluate_pairs(images, masks)
        result["dataset_provenance"] = provenance
        result["source_archive_sha256"] = source_hashes
        return result

    run = execute(
        "segmentation_benchmark", {"max_side": 512, "kernel": 5}, work, provenance["id"]
    )
    summary = {
        "run_id": run["id"],
        **{k: v for k, v in run["result"].items() if k != "per_image"},
    }
    (output / "verification.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    run_benchmark()
