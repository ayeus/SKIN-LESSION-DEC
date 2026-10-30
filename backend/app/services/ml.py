"""Actual CNN training. No downloads, prediction defaults, or clinical efficacy claims."""

import hashlib
import json
from importlib.metadata import version
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image, ImageOps
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    balanced_accuracy_score,
    roc_auc_score,
    log_loss,
    roc_curve,
    precision_recall_curve,
)

SIZE = 224
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def preprocessing(training=False):
    steps = [transforms.Resize((SIZE, SIZE))]
    if training:
        steps += [transforms.RandomHorizontalFlip(), transforms.RandomRotation(15)]
    return transforms.Compose(
        steps + [transforms.ToTensor(), transforms.Normalize(MEAN, STD)]
    )


def split_metadata(df, seed=42):
    required = {"image_path", "label", "group_id"}
    if not required <= set(df):
        raise ValueError("Metadata requires image_path,label,group_id")
    if df[list(required)].isna().any().any():
        raise ValueError("Metadata has missing values")
    if df.image_path.duplicated().any():
        raise ValueError("Image paths must be unique")
    if df.label.nunique() < 2:
        raise ValueError("At least two real classes required")
    if df.groupby("label").group_id.nunique().min() < 5:
        raise ValueError(
            "At least five independent groups per class required for five-fold stratified group split"
        )
    folds = list(
        StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(
            df, df.label, df.group_id
        )
    )
    test = folds[0][1]
    val = folds[1][1]
    train = np.setdiff1d(np.arange(len(df)), np.r_[test, val])
    groups = [set(df.iloc[ix].group_id) for ix in (train, val, test)]
    if any(groups[i] & groups[j] for i, j in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("Group leakage detected")
    if any(set(df.iloc[ix].label) != set(df.label) for ix in (train, val, test)):
        raise ValueError("Split lacks classes; provide more independent groups")
    return train, val, test


def architecture(name, classes, pretrained=False):
    if name == "small_cnn" and pretrained:
        raise ValueError(
            "Small CNN has no ImageNet weights; choose ResNet/EfficientNet or disable pretraining"
        )
    if name == "resnet18":
        model = models.resnet18(
            weights=models.ResNet18_Weights.DEFAULT if pretrained else None
        )
        model.fc = nn.Linear(model.fc.in_features, classes)
    elif name == "efficientnet_b0":
        model = models.efficientnet_b0(
            weights=models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        )
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, classes)
    elif name == "small_cnn":
        model = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(32, classes),
        )
    else:
        raise ValueError(
            "Supported architectures: small_cnn, resnet18, efficientnet_b0"
        )
    return model


class Lesions(Dataset):
    def __init__(self, df, root, labels, training):
        self.df = df
        self.root = root.resolve()
        self.labels = labels
        self.transform = preprocessing(training)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, i):
        row = self.df.iloc[i]
        path = (self.root / row.image_path).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Image path escapes dataset root")
        with Image.open(path) as im:
            image = ImageOps.exif_transpose(im).convert("RGB")
            tensor = self.transform(image)
        return tensor, self.labels.index(str(row.label))


def classifier_head(model, name):
    return (
        model.fc
        if name == "resnet18"
        else model.classifier[1]
        if name == "efficientnet_b0"
        else model[-1]
    )


def evaluate(model, name, labels, df, indices, loader, output, partition):
    model.eval()
    truth = []
    scores = []
    embeddings = []
    head = classifier_head(model, name)
    handle = head.register_forward_pre_hook(
        lambda module, args: embeddings.extend(args[0].detach().cpu().tolist())
    )
    with torch.no_grad():
        for x, y in loader:
            truth += y.tolist()
            scores += model(x).softmax(1).tolist()
    handle.remove()
    features = pd.DataFrame(
        embeddings, columns=[f"feature_{i}" for i in range(len(embeddings[0]))]
    )
    features["label"] = [labels[i] for i in truth]
    features["group_id"] = df.iloc[indices].group_id.to_numpy()
    features.to_csv(output / f"{partition}_embeddings.csv", index=False)
    scores = np.asarray(scores, dtype=np.float64)
    scores /= scores.sum(axis=1, keepdims=True)
    pred = scores.argmax(1)
    evaluation = {
        "classification": classification_report(
            truth,
            pred,
            labels=list(range(len(labels))),
            target_names=labels,
            output_dict=True,
            zero_division=0,
        ),
        "balanced_accuracy": balanced_accuracy_score(truth, pred),
        "confusion_matrix": confusion_matrix(
            truth, pred, labels=list(range(len(labels)))
        ).tolist(),
        "log_loss": log_loss(truth, scores, labels=list(range(len(labels)))),
        "brier_multiclass": float(
            np.mean(np.sum((scores - np.eye(len(labels))[truth]) ** 2, axis=1))
        ),
        "roc_auc": roc_auc_score(truth, scores[:, 1])
        if len(labels) == 2
        else roc_auc_score(
            truth, scores, multi_class="ovr", labels=list(range(len(labels)))
        ),
    }
    # Actual class-wise curves, reliability bins and measured calibration error.
    curves = {}
    for index, label in enumerate(labels):
        binary = (np.asarray(truth) == index).astype(int)
        fpr, tpr, _ = roc_curve(binary, scores[:, index])
        precision, recall, _ = precision_recall_curve(binary, scores[:, index])
        curves[label] = {
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "precision": precision.tolist(),
            "recall": recall.tolist(),
        }
    reliability = []
    ece = 0.0
    confidence = scores.max(1)
    correct = pred == np.asarray(truth)
    for i in range(10):
        mask = (confidence >= i / 10) & (
            confidence < (i + 1) / 10 if i < 9 else confidence <= 1
        )
        if mask.any():
            average = float(confidence[mask].mean())
            accuracy = float(correct[mask].mean())
            count = int(mask.sum())
            ece += count / len(truth) * abs(average - accuracy)
            reliability.append(
                {
                    "lower": i / 10,
                    "upper": (i + 1) / 10,
                    "count": count,
                    "mean_score": average,
                    "accuracy": accuracy,
                }
            )
    evaluation.update(
        curves=curves,
        reliability=reliability,
        expected_calibration_error=ece,
        calibration_note=f"Measured on {partition}, 10 fixed-width bins; scores remain uncalibrated.",
    )
    return evaluation


def train(
    metadata,
    images,
    output,
    name="small_cnn",
    epochs=5,
    batch_size=16,
    seed=42,
    pretrained=False,
    progress_callback=None,
    defer_test=False,
    freeze_backbone=False,
):
    if not 1 <= epochs <= 1000 or not 1 <= batch_size <= 128:
        raise ValueError("Invalid epochs/batch size")
    training_source_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.use_deterministic_algorithms(True)
    df = pd.read_csv(metadata, dtype={"label": str, "group_id": str})
    train_ix, val_ix, test_ix = split_metadata(df, seed)
    from .image_audit import audit_images

    audit = audit_images(df, images)
    if not audit["ready"]:
        raise ValueError(
            "Image content audit failed: invalid files or identical image pixels/bytes across groups require review"
        )
    hashes = {row["encoded_sha256"] for row in audit["image_records"]}
    labels = sorted(df.label.unique())
    model = architecture(name, len(labels), pretrained)
    if freeze_backbone:
        if name == "small_cnn" or not pretrained:
            raise ValueError(
                "Frozen transfer baseline requires a pretrained ResNet/EfficientNet backbone"
            )
        for parameter in model.parameters():
            parameter.requires_grad_(False)
        for parameter in classifier_head(model, name).parameters():
            parameter.requires_grad_(True)
    loaders = [
        DataLoader(
            Lesions(df.iloc[ix], images, labels, i == 0),
            batch_size=batch_size,
            shuffle=i == 0,
            num_workers=0,
        )
        for i, ix in enumerate((train_ix, val_ix, test_ix))
    ]
    counts = df.iloc[train_ix].label.value_counts()
    weights = torch.tensor(
        [len(train_ix) / (len(labels) * counts[c]) for c in labels], dtype=torch.float32
    )
    loss_fn = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.Adam(
        (p for p in model.parameters() if p.requires_grad), lr=0.001
    )
    output.mkdir(parents=True, exist_ok=False)
    best = float("inf")
    history = []
    for epoch in range(epochs):
        totals = []
        for phase, loader in enumerate(loaders[:2]):
            model.train(phase == 0)
            if freeze_backbone:
                model.eval()  # keep frozen BatchNorm statistics fixed
                classifier_head(model, name).train(phase == 0)
            loss_sum = 0.0
            loss_weight = 0.0
            correct = 0
            n = 0
            with torch.set_grad_enabled(phase == 0):
                for x, y in loader:
                    logits = model(x)
                    loss = loss_fn(logits, y)
                    if phase == 0:
                        optimizer.zero_grad()
                        loss.backward()
                        optimizer.step()
                    batch_weight = float(weights[y].sum())
                    loss_sum += loss.item() * batch_weight
                    loss_weight += batch_weight
                    correct += (logits.argmax(1) == y).sum().item()
                    n += len(y)
            totals.append({"loss": loss_sum / loss_weight, "accuracy": correct / n})
        history.append(
            {"epoch": epoch + 1, "train": totals[0], "validation": totals[1]}
        )
        if totals[1]["loss"] < best:
            best = totals[1]["loss"]
            torch.save(model.state_dict(), output / "weights.pt")
        temporary = output / "history.tmp"
        temporary.write_text(json.dumps(history, indent=2))
        temporary.replace(output / "history.json")
        if progress_callback:
            progress_callback(history[-1])
    model.load_state_dict(torch.load(output / "weights.pt", weights_only=True))
    evaluation_partition = "validation" if defer_test else "test"
    evaluation = evaluate(
        model,
        name,
        labels,
        df,
        val_ix if defer_test else test_ix,
        loaders[1] if defer_test else loaders[2],
        output,
        evaluation_partition,
    )
    manifest = {
        "architecture": name,
        "training_source_sha256": training_source_sha256,
        "software_versions": {
            package: version(package)
            for package in [
                "torch",
                "torchvision",
                "numpy",
                "pandas",
                "scikit-learn",
                "Pillow",
            ]
        },
        "training_configuration": {
            "optimizer": "Adam",
            "learning_rate": 0.001,
            "loss": "class-weighted cross entropy",
            "class_weights": {
                label: float(weights[i]) for i, label in enumerate(labels)
            },
            "training_class_counts": {label: int(counts[label]) for label in labels},
            "cpu_threads": torch.get_num_threads(),
            "augmentation": {
                "horizontal_flip_probability": 0.5,
                "rotation_degrees": 15,
            },
        },
        "labels": labels,
        "size": SIZE,
        "mean": MEAN,
        "std": STD,
        "seed": seed,
        "epochs": epochs,
        "pretrained_imagenet": pretrained,
        "frozen_backbone": freeze_backbone,
        "evaluation_partition": evaluation_partition,
        "test_evaluated": not defer_test,
        "selection_criterion": "Minimum class-weighted validation loss; test is never used for checkpoint selection.",
        "best_validation_loss": best,
        "content_audit": {
            key: value
            for key, value in audit.items()
            if key
            not in {
                "image_records",
                "cross_group_encoded_duplicates",
                "cross_group_decoded_duplicates",
            }
        },
        "image_content_sha256": hashlib.sha256(
            "".join(sorted(hashes)).encode()
        ).hexdigest(),
        "metadata_sha256": hashlib.sha256(metadata.read_bytes()).hexdigest(),
        "weights_sha256": hashlib.sha256(
            (output / "weights.pt").read_bytes()
        ).hexdigest(),
        "split_indices": {
            "train": train_ix.tolist(),
            "validation": val_ix.tolist(),
            "test": test_ix.tolist(),
        },
        "group_semantics": "Owner must document patient vs lesion grouping; lesion IDs do not exclude same-patient leakage.",
        "calibrated": False,
        "research_only": True,
        "evaluation": evaluation,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def load_artifact(root):
    manifest = json.loads((root / "manifest.json").read_text())
    if (
        manifest.get("research_only") is not True
        or manifest.get("calibrated") is not False
    ):
        raise ValueError("Unsupported artifact safety metadata")
    if (
        manifest.get("size") != SIZE
        or manifest.get("mean") != MEAN
        or manifest.get("std") != STD
    ):
        raise ValueError("Artifact preprocessing mismatch")
    weights = root / "weights.pt"
    if hashlib.sha256(weights.read_bytes()).hexdigest() != manifest.get(
        "weights_sha256"
    ):
        raise ValueError("Model checksum mismatch")
    model = architecture(manifest["architecture"], len(manifest["labels"]))
    model.load_state_dict(torch.load(weights, map_location="cpu", weights_only=True))
    model.eval()
    return model, manifest


def predict(rgb, root):
    model, manifest = load_artifact(root)
    if manifest.get("test_evaluated") is False:
        raise ValueError(
            "Candidate has validation-only evaluation; complete frozen-choice test review before inference"
        )
    x = preprocessing()(Image.fromarray(rgb)).unsqueeze(0)
    with torch.no_grad():
        scores = model(x).softmax(1)[0].tolist()
    return {
        "scores": dict(zip(manifest["labels"], scores)),
        "research_prediction": manifest["labels"][int(np.argmax(scores))],
        "calibrated": False,
        "model_sha256": manifest["weights_sha256"],
        "limitation": "Uncalibrated research scores, not diagnostic confidence. External clinical validation has not been established.",
    }


def gradcam(rgb, root):
    from .images import uri
    import cv2

    model, manifest = load_artifact(root)
    if manifest.get("test_evaluated") is False:
        raise ValueError(
            "Validation-only candidate is not ready for inference explanations"
        )
    layer = (
        model.layer4[-1]
        if manifest["architecture"] == "resnet18"
        else model.features[-1]
        if manifest["architecture"] == "efficientnet_b0"
        else model[3]
    )
    activations = []
    gradients = []

    def hook(module, args, output):
        activations.append(output)
        output.register_hook(lambda gradient: gradients.append(gradient))

    handle = layer.register_forward_hook(hook)
    try:
        x = preprocessing()(Image.fromarray(rgb)).unsqueeze(0).requires_grad_(True)
        logits = model(x)
        index = int(logits.argmax(1))
        model.zero_grad()
        logits[0, index].backward()
        cam = (
            torch.relu(
                (gradients[0].mean(dim=(2, 3), keepdim=True) * activations[0]).sum(
                    dim=1
                )
            )[0]
            .detach()
            .numpy()
        )
        cam = cv2.resize(cam, (rgb.shape[1], rgb.shape[0]))
        peak = float(cam.max())
        if peak > 0:
            cam /= peak
        heat = cv2.cvtColor(
            cv2.applyColorMap(np.uint8(cam * 255), cv2.COLORMAP_TURBO),
            cv2.COLOR_BGR2RGB,
        )
        overlay = np.uint8(0.65 * rgb + 0.35 * heat)
        return {
            "class": manifest["labels"][index],
            "overlay": uri(overlay),
            "activation_peak": peak,
            "limitation": "Grad-CAM is a coarse gradient-based attribution, not an expert lesion mask or evidence of clinical reasoning.",
        }
    finally:
        handle.remove()


def finalize_test(root, metadata, images):
    """Evaluate a previously validation-only candidate after experiment choice is frozen."""
    model, manifest = load_artifact(root)
    if manifest.get("test_evaluated") is not False:
        raise ValueError("Independent test was already evaluated for this artifact")
    if hashlib.sha256(metadata.read_bytes()).hexdigest() != manifest["metadata_sha256"]:
        raise ValueError("Metadata changed since candidate training")
    df = pd.read_csv(metadata, dtype={"label": str, "group_id": str})
    hashes = set()
    for name in df.image_path:
        path = (images / name).resolve()
        if not path.is_relative_to(images.resolve()):
            raise ValueError("Image path escapes dataset root")
        hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
    if (
        hashlib.sha256("".join(sorted(hashes)).encode()).hexdigest()
        != manifest["image_content_sha256"]
    ):
        raise ValueError("Image source changed since candidate training")
    indices = manifest["split_indices"]["test"]
    loader = DataLoader(
        Lesions(df.iloc[indices], images, manifest["labels"], False),
        batch_size=16,
        shuffle=False,
        num_workers=0,
    )
    result = evaluate(
        model,
        manifest["architecture"],
        manifest["labels"],
        df,
        indices,
        loader,
        root,
        "test",
    )
    manifest["validation_evaluation"] = manifest["evaluation"]
    manifest["evaluation"] = result
    manifest["evaluation_partition"] = "test"
    manifest["test_evaluated"] = True
    temporary = root / "manifest.tmp"
    temporary.write_text(json.dumps(manifest, indent=2))
    temporary.replace(root / "manifest.json")
    return manifest
