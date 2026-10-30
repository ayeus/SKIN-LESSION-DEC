"""Actual isolated U-Net fitting on synthetic geometry, never clinical results."""

import io
from uuid import uuid4
from zipfile import ZipFile
import numpy as np
import pytest
import torch
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.services.segmentation_model import (
    TinyUNet,
    train,
    load_pairs,
    resize_rgb,
    load_artifact,
)
from backend.app.services.images import decode
from backend.app.db import ROOT
from backend.app.main import app, execute

TOKEN = {"Authorization": "Bearer synthetic-test-token-not-a-secret"}


def test_unet_preserves_geometry_and_propagates_input_gradients():
    torch.manual_seed(42)
    model = TinyUNet()
    x = torch.rand(2, 3, 32, 48, requires_grad=True)
    y = model(x)
    assert y.shape == (2, 1, 32, 48)
    y.mean().backward()
    assert (
        float(x.grad.abs().sum()) > 0
        and float(model.first[0].weight.grad.abs().sum()) > 0
    )


def test_actual_training_preprocessing_selection_and_uploaded_image_inference(
    tmp_path, monkeypatch
):
    paths = [tmp_path / "images.zip", tmp_path / "masks.zip"]
    first_bytes = None
    with ZipFile(paths[0], "w") as images, ZipFile(paths[1], "w") as masks:
        for i in range(20):
            height, width = (768, 1024) if i == 0 else (32, 48)
            rgb = np.random.default_rng(i).integers(
                100, 200, (height, width, 3), dtype=np.uint8
            )
            rgb[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4] = 30
            mask = np.zeros((height, width), dtype=np.uint8)
            mask[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4] = 255
            encoded = io.BytesIO()
            Image.fromarray(rgb).save(encoded, format="JPEG", quality=95)
            if i == 0:
                first_bytes = encoded.getvalue()
            images.writestr(f"synthetic_{i:02d}.jpg", encoded.getvalue())
            encoded = io.BytesIO()
            Image.fromarray(mask).save(encoded, format="PNG")
            masks.writestr(f"synthetic_{i:02d}_segmentation.png", encoded.getvalue())
    cache = load_pairs(*paths)
    # High-resolution textured source exposes JPEG-draft vs full-RGB resize drift.
    np.testing.assert_array_equal(cache[0]["rgb"], resize_rgb(decode(first_bytes)))
    monkeypatch.delenv("DERMA_SEGMENTATION_MODEL", raising=False)
    pointer = ROOT / "segmentation-model-selection.json"
    try:
        with TestClient(app) as client:

            def fit(identifier):
                manifest = train(
                    *paths, ROOT / "segmentation_models" / identifier, epochs=1
                )
                return {
                    "segmentation_training_run_id": identifier,
                    "manifest": manifest,
                }

            run = execute(
                "segmentation_training",
                {"fixture": "explicit synthetic geometric test"},
                fit,
            )
            manifest = run["result"]["manifest"]
            assert sum(len(v) for v in manifest["split_image_ids"].values()) == 20
            assert (
                client.post("/segmentation-models/select/" + run["id"]).status_code
                == 401
            )
            selected = client.post(
                "/segmentation-models/select/" + run["id"], headers=TOKEN
            )
            assert selected.status_code == 200, selected.text
            assert (
                client.get("/status", headers=TOKEN).json()[
                    "segmentation_model_available"
                ]
                is True
            )
            result = client.post(
                "/images/process",
                headers=TOKEN,
                data={"method": "learned_segmentation", "parameters": "{}"},
                files={
                    "file": ("synthetic-high-resolution.jpg", first_bytes, "image/jpeg")
                },
            )
            assert result.status_code == 200, result.text
            assert result.json()["result"]["metrics"]["model"] == "tiny_unet_v2"
            assert (
                result.json()["result"]["metrics"]["weights_sha256"]
                == manifest["weights_sha256"]
            )
            import base64

            mask = decode(
                base64.b64decode(result.json()["result"]["mask"].split(",")[1])
            )
            assert mask.shape == (768, 1024, 3) and set(np.unique(mask)) <= {0, 255}
            weights = ROOT / "segmentation_models" / run["id"] / "weights.pt"
            with weights.open("ab") as stream:
                stream.write(b"corrupted")
            with pytest.raises(ValueError, match="checksum"):
                load_artifact(weights.parent)
            assert (
                client.get("/status", headers=TOKEN).json()[
                    "segmentation_model_available"
                ]
                is False
            )
    finally:
        pointer.unlink(missing_ok=True)
