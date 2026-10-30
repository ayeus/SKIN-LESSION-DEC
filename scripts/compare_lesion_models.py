"""Validation-only architecture comparison; expose test once for the frozen choice.

Uses the entire configured genuine cohort, never a hidden synthetic/subsampled
replacement. Pretrained head-only transfer is a documented compute baseline,
not a claim of fully fine-tuned or clinically effective lesion models.
"""

import argparse
import json
from pathlib import Path
from uuid import uuid4
from backend.app.db import ROOT, Session, Run
from backend.app.main import execute
from backend.app import training
from backend.app.services.ml import train, finalize_test


def compare(epochs=3, batch_size=16):
    ready = training.readiness()
    if not ready["ready"]:
        raise ValueError(ready["reason"])
    metadata, images = training.source_paths()
    from backend.app.services.public_image_registry import register_lesion_manifest

    provenance = register_lesion_manifest(metadata)
    identifier = str(uuid4())
    directory = ROOT / "experiments" / identifier
    directory.mkdir(parents=True, exist_ok=False)
    plan = {
        "experiment_id": identifier,
        "dataset_provenance": provenance,
        "epochs_per_candidate": epochs,
        "batch_size": batch_size,
        "seed": 42,
        "criterion": "Minimum class-weighted validation loss; first candidate wins ties. Held-out test never selects candidate.",
        "candidates": [
            {
                "architecture": "small_cnn",
                "pretrained": False,
                "freeze_backbone": False,
            },
            {"architecture": "resnet18", "pretrained": True, "freeze_backbone": True},
            {
                "architecture": "efficientnet_b0",
                "pretrained": True,
                "freeze_backbone": True,
            },
        ],
        "limitations": "Fixed short CPU compute budget; transfer candidates train classifier heads only with frozen ImageNet backbone and BatchNorm statistics. Full fine-tuning/hyperparameter search, patient-independent/external/skin-tone validation remain incomplete.",
    }
    (directory / "plan.json").write_text(json.dumps(plan, indent=2))
    results = []
    for candidate in plan["candidates"]:
        params = {
            **candidate,
            "epochs": epochs,
            "batch_size": batch_size,
            "seed": 42,
            "defer_test": True,
            "experiment_id": identifier,
        }

        def work(run_id):
            def progress(value):
                print(
                    json.dumps({"candidate": candidate["architecture"], **value}),
                    flush=True,
                )
                with Session() as session:
                    row = session.get(Run, run_id)
                    row.result = {
                        "epoch": value["epoch"],
                        "total_epochs": epochs,
                        "latest": value,
                    }
                    session.commit()

            manifest = train(
                metadata,
                images,
                training.artifact_dir(run_id),
                name=candidate["architecture"],
                epochs=epochs,
                batch_size=batch_size,
                pretrained=candidate["pretrained"],
                freeze_backbone=candidate["freeze_backbone"],
                defer_test=True,
                progress_callback=progress,
            )
            return {
                "training_run_id": run_id,
                "manifest": manifest,
                "history": json.loads(
                    (training.artifact_dir(run_id) / "history.json").read_text()
                ),
            }

        run = execute("training", params, work, provenance["id"])
        results.append(
            {
                "training_run_id": run["id"],
                "architecture": candidate["architecture"],
                "best_validation_loss": run["result"]["manifest"][
                    "best_validation_loss"
                ],
                "validation_evaluation": run["result"]["manifest"]["evaluation"],
                "test_evaluated": False,
            }
        )
        (directory / "validation-comparison.json").write_text(
            json.dumps(results, indent=2)
        )
    chosen = min(results, key=lambda r: r["best_validation_loss"])
    # Persist a frozen decision before any candidate's test predictions are produced.
    choice = {
        "experiment_id": identifier,
        "training_run_id": chosen["training_run_id"],
        "architecture": chosen["architecture"],
        "selection_criterion": plan["criterion"],
        "best_validation_loss": chosen["best_validation_loss"],
        "test_seen_at_selection": False,
    }
    (directory / "frozen-choice.json").write_text(json.dumps(choice, indent=2))
    rid = chosen["training_run_id"]
    root = training.artifact_dir(rid)

    def test(run_id):
        manifest = finalize_test(root, metadata, images)
        manifest["experiment_selection"] = choice
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2))
        return {
            "training_run_id": rid,
            "manifest": manifest,
            "history": json.loads((root / "history.json").read_text()),
            "experiment_selection": choice,
        }

    final = execute(
        "training",
        {"experiment_id": identifier, "frozen_choice": choice},
        test,
        run_id=rid,
        dataset_id=provenance["id"],
    )
    summary = {
        "plan": plan,
        "frozen_choice": choice,
        "selected_test_evaluation": final["result"]["manifest"]["evaluation"],
        "artifact_selected_for_inference": False,
    }
    (directory / "evaluation.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    compare(args.epochs, args.batch_size)
