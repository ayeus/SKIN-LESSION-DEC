"""Real authenticated HTTP selection/inference/export; no performance from smoke inputs."""

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import requests
from backend.app.db import ROOT, Session, Run
from sqlalchemy import select


def verify(training_run_id):
    source = json.loads(
        (ROOT / "processed/public/maccrobat2020/source-validation.json").read_text()
    )
    with Session() as session:
        chosen = session.get(Run, training_run_id)
    if (
        chosen is None
        or chosen.kind != "clinical_ner_training"
        or chosen.status != "completed"
    ):
        raise ValueError(
            "Select an explicitly reviewed, completed real clinical NER training run"
        )
    report = json.loads((ROOT / "processed" / chosen.id / "report.json").read_text())
    # Explicit review of measured held-out evidence before selection. No automatic training promotion.
    metrics = report["evaluation"]["test_metrics"]["micro"]
    print(
        json.dumps({"reviewed_run": chosen.id, "measured_held_out_test": metrics}),
        flush=True,
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "DERMA_API_TOKEN": secrets.token_urlsafe(32)}
    env.pop("DERMA_NER_MODEL", None)
    headers = {"Authorization": "Bearer " + env["DERMA_API_TOKEN"]}
    base = f"http://127.0.0.1:{port}"

    def call(method, path, **kwargs):
        response = requests.request(
            method, base + path, headers=headers, timeout=120, **kwargs
        )
        response.raise_for_status()
        return response

    with (ROOT / "public-ner-http.log").open("w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError(
                        "Verification API exited; inspect public-ner-http.log"
                    )
                try:
                    if requests.get(base + "/health", timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Local verification API did not become ready")
            selected = call("POST", "/clinical-models/select/" + chosen.id).json()
            current = call("GET", "/clinical-models/current").json()
            assert current["model_card"]["evaluation"]["micro"] == metrics
            result = call(
                "POST",
                "/analyze/text",
                json={
                    "dataset_id": source["dataset_id"],
                    "parameters": {"task": "ner", "text_column": "text"},
                },
            ).json()
            exported = call("GET", f"/runs/{result['id']}/export/json").json()
            assert exported == result["result"]
            documents = exported["documents"]
            assert len(documents) == source["documents"]
            for document in documents:
                for entity in document["entities"]:
                    assert (
                        document["text"][entity["start"] : entity["end"]]
                        == entity["text"]
                    )
                    assert entity["negated"] is None
            summary = {
                "training_run_id": chosen.id,
                "artifact_id": selected["artifact_id"],
                "inference_run_id": result["id"],
                "documents_processed": len(documents),
                "predicted_entity_spans": sum(len(d["entities"]) for d in documents),
                "exact_export_roundtrip": True,
                "test_metrics_from_separate_held_out_training_protocol": metrics,
                "limitation": "HTTP smoke inputs include training documents. No inference-smoke accuracy is claimed. Separate document-disjoint test metrics are from the original training protocol; no clinical effectiveness, assertion or negation verification.",
            }
            (
                ROOT / "processed/public/maccrobat2020/ner-http-verification.json"
            ).write_text(json.dumps(summary, indent=2))
            print(json.dumps(summary, indent=2))
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--training-run",
        required=True,
        help="Explicit completed run ID reviewed before research selection",
    )
    verify(parser.parse_args().training_run)
