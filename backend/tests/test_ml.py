import numpy as np
import pandas as pd
import pytest
import torch
from PIL import Image
from backend.app.services.ml import split_metadata, architecture, preprocessing


def test_group_split_no_leakage():
    df = pd.DataFrame(
        [
            {
                "image_path": f"{label}-{g}-{j}.png",
                "label": label,
                "group_id": f"{label}-{g}",
            }
            for label in ["a", "b"]
            for g in range(10)
            for j in range(2)
        ]
    )
    train, val, test = split_metadata(df)
    assert len(train) + len(val) + len(test) == len(df)
    groups = [set(df.iloc[ix].group_id) for ix in (train, val, test)]
    assert (
        not groups[0] & groups[1]
        and not groups[0] & groups[2]
        and not groups[1] & groups[2]
    )
    with pytest.raises(ValueError):
        split_metadata(df.drop(columns="group_id"))


def test_tensor_preprocessing_and_eval_determinism():
    torch.manual_seed(42)
    m = architecture("small_cnn", 3)
    m.eval()
    x = preprocessing()(Image.fromarray(np.full((64, 80, 3), 128, np.uint8))).unsqueeze(
        0
    )
    assert x.shape == (1, 3, 224, 224)
    with torch.no_grad():
        a = m(x)
        b = m(x)
    assert a.shape == (1, 3)
    torch.testing.assert_close(a, b, rtol=0, atol=0)


def test_actual_training_checkpoint_roundtrip_and_gradcam(tmp_path):
    """Explicitly synthetic artifact test; never used in app data or medical claims."""
    from backend.app.services.ml import train, load_artifact, predict, gradcam
    import json

    images = tmp_path / "images"
    images.mkdir()
    rows = []
    for label in ("a", "b"):
        for g in range(10):
            rgb = np.random.default_rng(g + (100 if label == "b" else 0)).integers(
                0, 256, (32, 32, 3), dtype=np.uint8
            )
            name = f"{label}-{g}.png"
            Image.fromarray(rgb).save(images / name)
            rows.append(
                {"image_path": name, "label": label, "group_id": f"{label}-{g}"}
            )
    metadata = tmp_path / "metadata.csv"
    pd.DataFrame(rows).to_csv(metadata, index=False)
    output = tmp_path / "synthetic-artifact"
    manifest = train(metadata, images, output, epochs=1, batch_size=4)
    assert (output / "weights.pt").is_file() and (output / "manifest.json").is_file()
    assert (
        manifest["evaluation"]["confusion_matrix"] and manifest["calibrated"] is False
    )
    model, loaded = load_artifact(output)
    rgb = np.full((32, 32, 3), 128, np.uint8)
    a = predict(rgb, output)
    b = predict(rgb, output)
    assert a == b
    assert sum(a["scores"].values()) == pytest.approx(1, abs=1e-6)
    explanation = gradcam(rgb, output)
    assert explanation["overlay"].startswith("data:image/png;base64,")
    assert explanation["activation_peak"] >= 0
    with (output / "weights.pt").open("ab") as stream:
        stream.write(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        load_artifact(output)


def test_small_baseline_cannot_claim_imagenet_pretraining():
    with pytest.raises(ValueError, match="no ImageNet weights"):
        architecture("small_cnn", 2, pretrained=True)


def test_candidate_defers_test_pixels_until_finalization_and_blocks_promotion(
    tmp_path, monkeypatch
):
    """Isolated synthetic pixels verify protocol access, not model effectiveness."""
    from backend.app.services.ml import train, finalize_test, Lesions, predict
    from backend.app import training
    from backend.app.main import model_ready

    images = tmp_path / "images"
    images.mkdir()
    rows = []
    for label in ["a", "b"]:
        for i in range(10):
            name = f"{label}-{i}.png"
            Image.fromarray(
                np.random.default_rng(i + (100 if label == "b" else 0)).integers(
                    0, 256, (24, 24, 3), dtype=np.uint8
                )
            ).save(images / name)
            rows.append({"image_path": name, "label": label, "group_id": name})
    metadata = tmp_path / "metadata.csv"
    frame = pd.DataFrame(rows)
    frame.to_csv(metadata, index=False)
    output = tmp_path / "candidate"
    accessed = []
    original = Lesions.__getitem__

    def record(self, index):
        accessed.append(self.df.iloc[index].image_path)
        return original(self, index)

    monkeypatch.setattr(Lesions, "__getitem__", record)
    manifest = train(metadata, images, output, epochs=1, batch_size=4, defer_test=True)
    test_paths = set(frame.iloc[manifest["split_indices"]["test"]].image_path)
    assert not test_paths & set(accessed)
    assert (
        manifest["evaluation_partition"] == "validation"
        and manifest["test_evaluated"] is False
    )
    assert (
        not (output / "test_embeddings.csv").exists()
        and (output / "validation_embeddings.csv").is_file()
    )
    monkeypatch.setenv("DERMA_MODEL_DIR", str(output))
    assert model_ready() is False
    with pytest.raises(ValueError, match="validation-only"):
        predict(np.zeros((24, 24, 3), np.uint8), output)
    monkeypatch.setattr(training, "artifact_dir", lambda run_id: output)
    with pytest.raises(ValueError, match="Validation-only"):
        training.select_artifact("test-only")
    path = images / next(iter(test_paths))
    original_bytes = path.read_bytes()
    path.write_bytes(original_bytes + b"changed")
    with pytest.raises(ValueError, match="source changed"):
        finalize_test(output, metadata, images)
    path.write_bytes(original_bytes)
    finalized = finalize_test(output, metadata, images)
    assert (
        finalized["test_evaluated"] is True
        and finalized["evaluation_partition"] == "test"
    )
    assert test_paths <= set(accessed) and (output / "test_embeddings.csv").is_file()
    assert model_ready() is True
    with pytest.raises(ValueError, match="already evaluated"):
        finalize_test(output, metadata, images)


def test_patient_group_can_legitimately_contain_different_lesion_labels():
    frame = pd.DataFrame(
        [
            {
                "image_path": f"{group}-{label}.png",
                "group_id": f"patient-{group}",
                "label": label,
            }
            for group in range(10)
            for label in ["a", "b"]
        ]
    )
    splits = split_metadata(frame)
    groups = [set(frame.iloc[indices].group_id) for indices in splits]
    assert all(set(frame.iloc[indices].label) == {"a", "b"} for indices in splits)
    assert (
        not groups[0] & groups[1]
        and not groups[0] & groups[2]
        and not groups[1] & groups[2]
    )
