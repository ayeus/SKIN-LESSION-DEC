"""Actual compact U-Net research model; explicit local source and operating point."""

import hashlib
import io
import json
import os
from pathlib import Path
from uuid import UUID
from zipfile import ZipFile
import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from ..db import ROOT
from .images import mask_metrics

SIZE = 256


class TinyUNetV1(nn.Module):
    def __init__(self):
        super().__init__()

        def block(a, b):
            return nn.Sequential(
                nn.Conv2d(a, b, 3, padding=1),
                nn.ReLU(),
                nn.Conv2d(b, b, 3, padding=1),
                nn.ReLU(),
            )

        self.first = block(3, 8)
        self.second = block(8, 16)
        self.bottom = block(16, 32)
        self.up_second = block(48, 16)
        self.up_first = block(24, 8)
        self.out = nn.Conv2d(8, 1, 1)

    def forward(self, x):
        a = self.first(x)
        b = self.second(nn.functional.max_pool2d(a, 2))
        c = self.bottom(nn.functional.max_pool2d(b, 2))
        d = self.up_second(
            torch.cat(
                [
                    nn.functional.interpolate(
                        c, size=b.shape[-2:], mode="bilinear", align_corners=False
                    ),
                    b,
                ],
                1,
            )
        )
        return self.out(
            self.up_first(
                torch.cat(
                    [
                        nn.functional.interpolate(
                            d, size=a.shape[-2:], mode="bilinear", align_corners=False
                        ),
                        a,
                    ],
                    1,
                )
            )
        )


class TinyUNet(TinyUNetV1):
    def __init__(self):
        super().__init__()

        def block(inputs, outputs):
            return nn.Sequential(
                nn.Conv2d(inputs, outputs, 3, padding=1, bias=False),
                nn.GroupNorm(4, outputs),
                nn.LeakyReLU(0.1),
                nn.Conv2d(outputs, outputs, 3, padding=1, bias=False),
                nn.GroupNorm(4, outputs),
                nn.LeakyReLU(0.1),
            )

        self.first = block(3, 8)
        self.second = block(8, 16)
        self.bottom = block(16, 32)
        self.up_second = block(48, 16)
        self.up_first = block(24, 8)


class Pairs(Dataset):
    def __init__(self, cache, indices, augment=False):
        self.cache = cache
        self.indices = indices
        self.augment = augment

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        row = self.cache[self.indices[index]]
        x = torch.from_numpy(row["rgb"].copy()).permute(2, 0, 1).float() / 255
        y = torch.from_numpy(row["mask"].copy()).unsqueeze(0).float() / 255
        if self.augment and torch.rand(()) < 0.5:
            x = x.flip(-1)
            y = y.flip(-1)
        return x, y


def probabilities(model, cache, indices):
    model.eval()
    result = []
    with torch.no_grad():
        for x, y in DataLoader(Pairs(cache, indices), batch_size=8, shuffle=False):
            result.extend(model(x).sigmoid().squeeze(1).numpy())
    return result


def measurements(cache, indices, predicted, threshold):
    rows = [
        {
            "source_image_id": cache[index]["id"],
            **mask_metrics((score >= threshold).astype(np.uint8), cache[index]["mask"]),
        }
        for index, score in zip(indices, predicted)
    ]
    return {
        "mean_dice": float(np.mean([r["dice"] for r in rows])),
        "mean_iou": float(np.mean([r["iou"] for r in rows])),
        "per_image": rows,
    }


def resize_rgb(rgb):
    return np.asarray(
        Image.fromarray(rgb).resize((SIZE, SIZE), Image.Resampling.BILINEAR)
    )


def load_pairs(images_path, masks_path):
    from scripts.verify_public_segmentation import members

    cache = []
    with ZipFile(images_path) as images, ZipFile(masks_path) as masks:
        image_files = members(images, ".jpg")
        mask_files = members(masks, "_segmentation.png")
        if {
            name.removesuffix("_segmentation.png") + ".jpg" for name in mask_files
        } != set(image_files):
            raise ValueError("Training image/mask pairing mismatch")
        for name in sorted(image_files):
            key = Path(name).stem
            with Image.open(io.BytesIO(images.read(image_files[name]))) as image:
                if image.width * image.height > 32_000_000 or image.getexif().get(
                    274
                ) not in (None, 1):
                    raise ValueError(
                        "Offline source exceeds 32M pixels or needs explicit mask orientation alignment"
                    )
                original_size = image.size
                rgb = resize_rgb(np.asarray(image.convert("RGB")))
            with Image.open(
                io.BytesIO(masks.read(mask_files[key + "_segmentation.png"]))
            ) as mask:
                if mask.size != original_size:
                    raise ValueError("Source mask has wrong shape")
                values = np.asarray(mask)
                if not set(np.unique(values)) <= {0, 255}:
                    raise ValueError("Expert mask must be binary")
                target = np.asarray(
                    mask.convert("L").resize((SIZE, SIZE), Image.Resampling.NEAREST)
                )
            cache.append({"id": key, "rgb": rgb, "mask": target})
    return cache


def train(images_path, masks_path, output, epochs=20, seed=42, progress_callback=None):
    if not isinstance(epochs, int) or not 1 <= epochs <= 200:
        raise ValueError("Segmentation epochs must be 1–200")
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.use_deterministic_algorithms(True)
    cache = load_pairs(images_path, masks_path)
    if len(cache) < 20:
        raise ValueError(
            "At least 20 actual annotated images required for local 70/15/15 split"
        )
    order = np.random.default_rng(seed).permutation(len(cache))
    a = int(len(order) * 0.7)
    b = int(len(order) * 0.85)
    train_indices, val_indices, test_indices = order[:a], order[a:b], order[b:]
    model = TinyUNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_fn = nn.BCEWithLogitsLoss()
    loader = DataLoader(
        Pairs(cache, train_indices, True), batch_size=8, shuffle=True, num_workers=0
    )
    output.mkdir(parents=True, exist_ok=False)
    history = []
    best = -1.0
    best_threshold = None
    best_epoch = None
    for epoch in range(epochs):
        model.train()
        total = 0.0
        count = 0
        for x, y in loader:
            logits = model(x)
            scores = logits.sigmoid()
            dice = (2 * (scores * y).sum((1, 2, 3)) + 1) / (
                scores.sum((1, 2, 3)) + y.sum((1, 2, 3)) + 1
            )
            loss = loss_fn(logits, y) + (1 - dice).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += loss.item() * len(y)
            count += len(y)
        predictions = probabilities(model, cache, val_indices)
        choices = [
            (threshold, measurements(cache, val_indices, predictions, threshold))
            for threshold in [0.25, 0.5, 0.75]
        ]
        threshold, evaluation = max(choices, key=lambda v: v[1]["mean_dice"])
        entry = {
            "epoch": epoch + 1,
            "loss": total / count,
            "validation": {
                "dice": evaluation["mean_dice"],
                "iou": evaluation["mean_iou"],
                "threshold": threshold,
            },
        }
        history.append(entry)
        if evaluation["mean_dice"] > best:
            best = evaluation["mean_dice"]
            best_threshold = threshold
            best_epoch = epoch + 1
            torch.save(model.state_dict(), output / "weights.pt")
        (output / "history.json").write_text(json.dumps(history, indent=2))
        if progress_callback:
            progress_callback(entry)
    model.load_state_dict(
        torch.load(output / "weights.pt", map_location="cpu", weights_only=True)
    )
    model.eval()
    test = measurements(
        cache, test_indices, probabilities(model, cache, test_indices), best_threshold
    )
    baseline = {}
    for method in ["otsu", "morphology"]:
        predicted = []
        for index in test_indices:
            gray = cv2.cvtColor(cache[index]["rgb"], cv2.COLOR_RGB2GRAY)
            _, mask = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
            )
            if method == "morphology":
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
            predicted.append(mask.astype(float) / 255)
        baseline[method] = measurements(cache, test_indices, predicted, 0.5)
    source_hashes = {}
    for source in [images_path, masks_path]:
        with source.open("rb") as stream:
            source_hashes[source.name] = hashlib.file_digest(
                stream, "sha256"
            ).hexdigest()
    manifest = {
        "model_name": "tiny_unet_v2",
        "architecture": {
            "channels": [8, 16, 32],
            "normalization": "four-group GroupNorm",
            "activation": "LeakyReLU slope .1",
        },
        "input_size": SIZE,
        "scale": "RGB / 255, shared full-RGB square bilinear resize; nearest mask resize",
        "threshold": best_threshold,
        "threshold_selection": "Grid [.25,.5,.75], maximize mean validation Dice with checkpoint; first wins ties. No test-based selection.",
        "seed": seed,
        "epochs": epochs,
        "best_epoch": best_epoch,
        "best_validation_dice": best,
        "split_image_ids": {
            key: [cache[i]["id"] for i in indices]
            for key, indices in [
                ("train", train_indices),
                ("validation", val_indices),
                ("test", test_indices),
            ]
        },
        "test_metrics": test,
        "classical_baselines_same_test_representation": baseline,
        "source_archive_sha256": source_hashes,
        "weights_sha256": hashlib.sha256(
            (output / "weights.pt").read_bytes()
        ).hexdigest(),
        "research_only": True,
        "calibrated": False,
        "limitation": "Local image-disjoint research split within the 100-image official ISIC2018 validation cohort, not official challenge training/test or patient-independent validation. Square 256px representation loses detail; upsampled masks are not validated native-resolution lesion boundaries or diagnostic evidence.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def selected_directory():
    configured = os.getenv("DERMA_SEGMENTATION_MODEL")
    if configured:
        return Path(configured)
    pointer = ROOT / "segmentation-model-selection.json"
    if not pointer.is_file():
        return None
    identifier = str(UUID(json.loads(pointer.read_text())["training_run_id"]))
    return ROOT / "segmentation_models" / identifier


def load_artifact(root):
    manifest = json.loads((root / "manifest.json").read_text())
    if (
        manifest.get("model_name") not in {"tiny_unet_v1", "tiny_unet_v2"}
        or manifest.get("input_size") != SIZE
        or manifest.get("research_only") is not True
        or manifest.get("calibrated") is not False
        or manifest.get("scale")
        != "RGB / 255, shared full-RGB square bilinear resize; nearest mask resize"
    ):
        raise ValueError(
            "Unsupported segmentation artifact/preprocessing safety metadata"
        )
    if manifest.get("threshold") not in [0.25, 0.5, 0.75]:
        raise ValueError("Missing measured validation-selected operating point")
    if hashlib.sha256((root / "weights.pt").read_bytes()).hexdigest() != manifest.get(
        "weights_sha256"
    ):
        raise ValueError("Segmentation weights checksum mismatch")
    model = TinyUNet() if manifest["model_name"] == "tiny_unet_v2" else TinyUNetV1()
    model.load_state_dict(
        torch.load(root / "weights.pt", map_location="cpu", weights_only=True)
    )
    model.eval()
    return model, manifest


def select_artifact(identifier):
    identifier = str(UUID(identifier))
    root = ROOT / "segmentation_models" / identifier
    _, manifest = load_artifact(root)
    path = ROOT / "segmentation-model-selection.json"
    temporary = path.with_suffix(".tmp")
    payload = {
        "training_run_id": identifier,
        "weights_sha256": manifest["weights_sha256"],
        "research_only": True,
    }
    temporary.write_text(json.dumps(payload))
    temporary.replace(path)
    return payload


def predict_mask(rgb):
    root = selected_directory()
    if root is None:
        raise ValueError("BLOCKED: no reviewed trained segmentation model selected")
    model, manifest = load_artifact(root)
    image = resize_rgb(rgb)
    x = torch.from_numpy(image.copy()).permute(2, 0, 1).float().unsqueeze(0) / 255
    with torch.no_grad():
        score = model(x).sigmoid().squeeze().numpy()
    score = cv2.resize(
        score, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR
    )
    return (score >= manifest["threshold"]).astype(np.uint8) * 255, {
        "model": manifest["model_name"],
        "weights_sha256": manifest["weights_sha256"],
        "validation_selected_threshold": manifest["threshold"],
        "model_input_size": SIZE,
        "limitation": manifest["limitation"],
    }
