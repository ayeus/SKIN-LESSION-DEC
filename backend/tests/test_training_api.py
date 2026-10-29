"""Actual tiny training on isolated synthetic pixels; never a real lesion artifact."""

import os
import time
import numpy as np
import pandas as pd
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app

H = {"Authorization": "Bearer synthetic-test-token-not-a-secret"}


def test_missing_dataset_blocks_and_does_not_promote(monkeypatch, tmp_path):
    monkeypatch.setenv("DERMA_LESION_METADATA", str(tmp_path / "absent.csv"))
    with TestClient(app) as client:
        assert client.get("/training/readiness").status_code == 401
        assert client.get("/training/readiness", headers=H).json()["ready"] is False
        assert client.post("/training", headers=H, json={}).status_code == 409
        assert (
            client.post("/training", headers=H, json={"epochs": 0}).status_code == 422
        )
        assert (
            client.post(
                "/training",
                headers=H,
                json={"architecture": "small_cnn", "pretrained": True},
            ).status_code
            == 422
        )
        assert client.post("/models/select/not-present", headers=H).status_code == 404


def test_training_progress_artifact_selection_and_real_inference(monkeypatch, tmp_path):
    from backend.app.db import ROOT

    monkeypatch.delenv("DERMA_MODEL_DIR", raising=False)
    images = tmp_path / "images"
    images.mkdir()
    rows = []
    for label in ["a", "b"]:
        for group in range(10):
            name = f"{label}-{group}.png"
            pixels = np.random.default_rng(
                group + (100 if label == "b" else 0)
            ).integers(0, 256, (32, 32, 3), dtype=np.uint8)
            Image.fromarray(pixels).save(images / name)
            rows.append({"image_path": name, "label": label, "group_id": name})
    path = tmp_path / "metadata.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    monkeypatch.setenv("DERMA_LESION_METADATA", str(path))
    monkeypatch.setenv("DERMA_LESION_IMAGES", str(images))
    pointer = ROOT / "model-selection.json"
    try:
        with TestClient(app) as client:
            assert client.get("/training/readiness", headers=H).json()["ready"] is True
            job = client.post(
                "/training", headers=H, json={"epochs": 1, "batch_size": 4}
            )
            assert job.status_code == 200, job.text
            id = job.json()["id"]
            for _ in range(500):
                run = client.get("/runs/" + id, headers=H).json()
                if run["status"] in ["completed", "failed"]:
                    break
                time.sleep(0.02)
            assert run["status"] == "completed", run
            assert run["result"]["manifest"]["epochs"] == 1
            assert len(run["result"]["history"]) == 1
            assert not pointer.exists()  # No implicit promotion.
            selected = client.post("/models/select/" + id, headers=H)
            assert selected.status_code == 200, selected.text
            assert client.get("/models/current", headers=H).json()["manifest"][
                "research_only"
            ]
            output = client.post(
                "/inference",
                headers=H,
                files={
                    "file": (
                        "synthetic.png",
                        (images / "a-0.png").read_bytes(),
                        "image/png",
                    )
                },
            )
            assert output.status_code == 200, output.text
            assert set(output.json()["scores"]) == {"a", "b"}
    finally:
        pointer.unlink(missing_ok=True)  # Isolated test storage only.


def test_inference_retention_requires_explicit_opt_in(monkeypatch, tmp_path):
    """Reuse a test-only completed artifact produced by a real synthetic training test."""
    import json
    from backend.app.db import ROOT

    candidates = [p.parent for p in (ROOT / "models").glob("*/manifest.json")]
    if not candidates:
        # Test stands alone: train a tiny explicit synthetic artifact, never install it.
        from backend.app.services.ml import train

        images = tmp_path / "images"
        images.mkdir()
        rows = []
        for label in ["a", "b"]:
            for i in range(10):
                name = f"{label}-{i}.png"
                pixels = np.random.default_rng(
                    i + (100 if label == "b" else 0)
                ).integers(0, 256, (32, 32, 3), dtype=np.uint8)
                Image.fromarray(pixels).save(images / name)
                rows.append({"image_path": name, "label": label, "group_id": name})
        metadata = tmp_path / "m.csv"
        pd.DataFrame(rows).to_csv(metadata, index=False)
        artifact = tmp_path / "artifact"
        train(metadata, images, artifact, epochs=1, batch_size=4)
    else:
        artifact = candidates[0]
    monkeypatch.setenv("DERMA_MODEL_DIR", str(artifact))
    import io

    image = io.BytesIO()
    Image.fromarray(np.full((32, 32, 3), 128, np.uint8)).save(image, format="PNG")
    with TestClient(app) as client:
        before = [
            r for r in client.get("/runs", headers=H).json() if r["kind"] == "inference"
        ]
        files = {"file": ("synthetic.png", image.getvalue(), "image/png")}
        transient = client.post("/inference", headers=H, files=files)
        assert transient.status_code == 200 and "saved_run_id" not in transient.json()
        after = [
            r for r in client.get("/runs", headers=H).json() if r["kind"] == "inference"
        ]
        assert len(before) == len(after)
        saved = client.post(
            "/inference",
            headers=H,
            files=files,
            data={"retain": "true", "explain": "true"},
        )
        assert saved.status_code == 200, saved.text
        report = client.get("/runs/" + saved.json()["saved_run_id"], headers=H).json()[
            "result"
        ]
        assert (
            report["scores"] == saved.json()["scores"]
            and len(report["input_rgb_sha256"]) == 64
        )
        assert "explanation" not in report and "data:image" not in json.dumps(report)


def test_acquisition_state_measures_partial_bytes_without_claiming_readiness(
    tmp_path, monkeypatch
):
    import json
    from backend.app import training

    monkeypatch.setattr(training, "ROOT", tmp_path)
    root = tmp_path / "raw/isic2018-task3"
    root.mkdir(parents=True)
    (root / "ISIC2018_Task3_Training_Input.zip.part").write_bytes(b"isolated-fixture")
    (root / "archive-resource.json").write_text(json.dumps({"expected_bytes": 100}))
    state = training.acquisition_state()
    assert state["state"] == "partial_archive" and state["bytes_on_disk"] == 16
    assert state["fraction_on_disk"] == 0.16 and "liveness" in state["note"]


def test_readiness_reports_missing_optional_ml_runtime(monkeypatch, tmp_path):
    import builtins
    from backend.app import training

    path = tmp_path / "metadata.csv"
    path.write_text("image_path,label,group_id\na.png,a,a\n")
    monkeypatch.setenv("DERMA_LESION_METADATA", str(path))
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if (
            name == "services.ml"
            and kwargs.get("level", args[3] if len(args) > 3 else 0) == 1
        ):
            raise ModuleNotFoundError("isolated missing-ML-runtime fixture")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    result = training.readiness()
    assert result["ready"] is False and "CNN runtime" in result["reason"]
