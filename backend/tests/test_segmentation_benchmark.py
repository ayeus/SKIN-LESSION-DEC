"""Known synthetic rectangle verifies paired benchmark math, never clinical quality."""

import io
from zipfile import ZipFile
import numpy as np
from PIL import Image
import pytest
from scripts.verify_public_segmentation import evaluate_pairs


def archives(tmp_path, bad_mask=False):
    rgb = np.full((32, 32, 3), 180, dtype=np.uint8)
    rgb[8:24, 8:24] = 30
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[8:24, 8:24] = 255
    if bad_mask:
        mask = mask[:16, :16]
    images = tmp_path / "images.zip"
    masks = tmp_path / "masks.zip"
    for path, name, array, format in [
        (images, "source/synthetic.jpg", rgb, "JPEG"),
        (masks, "masks/synthetic_segmentation.png", mask, "PNG"),
    ]:
        buffer = io.BytesIO()
        Image.fromarray(array).save(buffer, format=format, quality=100, subsampling=0)
        with ZipFile(path, "w") as archive:
            archive.writestr(name, buffer.getvalue())
    return images, masks


def test_known_rectangle_has_exact_overlap_with_paired_reference(tmp_path):
    result = evaluate_pairs(*archives(tmp_path))
    assert result["counts"] == {"images": 1, "expert_masks": 1}
    assert result["mean_metrics"] == {
        "otsu": {"dice": 1.0, "iou": 1.0},
        "morphology": {"dice": 1.0, "iou": 1.0},
    }
    assert len(result["per_image"]) == 2


def test_misaligned_masks_fail_instead_of_resizing_wrong_source(tmp_path):
    with pytest.raises(ValueError, match="matching binary expert mask"):
        evaluate_pairs(*archives(tmp_path, bad_mask=True))
