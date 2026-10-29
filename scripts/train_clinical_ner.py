"""Train genuine case-report NER; selection for application use remains explicit."""

import argparse
import json
from uuid import uuid4
from backend.app.db import ROOT, Session, Run
from backend.app.main import execute
from backend.app.services.ner_training import train

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=20)
    args = parser.parse_args()
    corpus = ROOT / "processed/public/maccrobat2020/corpus.json"
    if not corpus.is_file():
        raise SystemExit("Run scripts.acquire_public_clinical first")
    identifier = str(uuid4())
    output = ROOT / "nlp_models" / identifier
    parameters = {"epochs": args.epochs, "seed": 42, "corpus": "MACCROBAT2020"}

    def work(run_id):
        def progress(value):
            print(json.dumps(value), flush=True)
            with Session() as session:
                item = session.get(Run, run_id)
                item.result = {
                    "epoch": value["epoch"],
                    "total_epochs": args.epochs,
                    "latest": value,
                }
                session.commit()

        report = train(
            corpus,
            output,
            epochs=args.epochs,
            progress_callback=progress,
        )
        return {
            "training_run_id": identifier,
            "evaluation": report,
            "history": json.loads((output / "history.json").read_text()),
        }

    run = execute("clinical_ner_training", parameters, work, run_id=None)
    # Artifact ID is separate and explicit; API selection verifies this completed run's result.
    print(
        json.dumps(
            {
                "run_id": run["id"],
                "training_run_id": identifier,
                "status": run["status"],
                "test_metrics": run["result"]["evaluation"]["test_metrics"]["micro"],
            },
            indent=2,
        )
    )
