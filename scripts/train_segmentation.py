"""Genuine paired-mask U-Net research experiment, never automatic model promotion."""

import argparse
import json
from backend.app.db import ROOT, Session, Run
from backend.app.main import execute
from backend.app.services.segmentation_model import train

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=20)
    args = p.parse_args()
    import torch

    torch.set_num_threads(4)
    source = ROOT / "raw/isic2018-task1-validation"
    verification = json.loads(
        (ROOT / "processed/public/isic2018-segmentation/verification.json").read_text()
    )

    def work(run_id):
        def progress(value):
            print(json.dumps(value), flush=True)
            with Session() as session:
                run = session.get(Run, run_id)
                run.result = {
                    "epoch": value["epoch"],
                    "total_epochs": args.epochs,
                    "latest": value,
                }
                session.commit()

        output = ROOT / "segmentation_models" / run_id
        manifest = train(
            source / "ISIC2018_Task1-2_Validation_Input.zip",
            source / "ISIC2018_Task1_Validation_GroundTruth.zip",
            output,
            epochs=args.epochs,
            progress_callback=progress,
        )
        return {
            "segmentation_training_run_id": run_id,
            "manifest": manifest,
            "history": json.loads((output / "history.json").read_text()),
            "dataset_provenance": verification["dataset_provenance"],
        }

    result = execute(
        "segmentation_training",
        {"epochs": args.epochs, "seed": 42, "input_size": 256},
        work,
        verification["dataset_provenance"]["id"],
    )
    print(
        json.dumps(
            {
                "run_id": result["id"],
                "test_metrics": result["result"]["manifest"]["test_metrics"],
            },
            indent=2,
        )
    )
