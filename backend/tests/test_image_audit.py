"""Explicit synthetic image fixtures verify actual pixel/content checks."""

import pandas as pd
import numpy as np
from PIL import Image
from backend.app.services.image_audit import audit_images


def test_different_encodings_of_identical_pixels_block_cross_group_leakage(tmp_path):
    pixels = np.full((24, 24, 3), 90, dtype=np.uint8)
    Image.fromarray(pixels).save(tmp_path / "a.png", compress_level=0)
    Image.fromarray(pixels).save(tmp_path / "b.png", compress_level=9)
    frame = pd.DataFrame(
        [
            {"image_path": name, "group_id": str(i), "label": "a"}
            for i, name in enumerate(["a.png", "b.png"])
        ]
    )
    result = audit_images(frame, tmp_path)
    assert result["ready"] is False
    assert not result["cross_group_encoded_duplicates"]
    assert len(result["cross_group_decoded_duplicates"]) == 1
    assert result["decoded_images"] == 2
    # Same true group stays together; repeated images there do not create cross-split leakage.
    frame["group_id"] = "same-source-group"
    assert audit_images(frame, tmp_path)["ready"] is True


def test_corruption_and_missing_source_files_are_reported_without_substitution(
    tmp_path,
):
    (tmp_path / "broken.png").write_bytes(b"not an image")
    frame = pd.DataFrame(
        [
            {"image_path": name, "group_id": str(i), "label": "a"}
            for i, name in enumerate(["broken.png", "absent.png"])
        ]
    )
    report = audit_images(frame, tmp_path)
    assert report["ready"] is False and report["decoded_images"] == 0
    assert len(report["invalid_images"]) == 2 and not report["image_records"]
