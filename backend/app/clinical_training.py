"""Explicit, administrator-controlled selection of actual NER artifacts."""

import hashlib
import json
import os
from pathlib import Path
from uuid import UUID
from .db import ROOT


def validate_model(root):
    card = json.loads((root / "research-model-card.json").read_text())
    if not all(
        card.get(k) for k in ["source", "license", "intended_use", "limitations"]
    ):
        raise ValueError(
            "Clinical model card requires source, license, intended_use and limitations"
        )
    for relative, expected in card.get("files_sha256", {}).items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("NER artifact file missing or escapes model directory")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("NER artifact checksum mismatch")
    return card


def selected_directory():
    configured = os.getenv("DERMA_NER_MODEL")
    if configured:
        return Path(configured)
    pointer = ROOT / "clinical-model-selection.json"
    if not pointer.is_file():
        return None
    value = json.loads(pointer.read_text())
    identifier = str(UUID(value["artifact_id"]))
    return ROOT / "nlp_models" / identifier / "pipeline"


def select_artifact(artifact_id, run_id):
    identifier = str(UUID(artifact_id))
    root = ROOT / "nlp_models" / identifier / "pipeline"
    card = validate_model(root)
    if not card.get("files_sha256") or not card.get("evaluation"):
        raise ValueError("Select only evaluated, checksum-tracked local NER artifacts")
    import spacy

    if "ner" not in spacy.load(root).pipe_names:
        raise ValueError("Artifact lacks a trained NER component")
    payload = {
        "artifact_id": identifier,
        "training_run_id": run_id,
        "research_only": True,
        "clinical_validation": "Not established",
    }
    path = ROOT / "clinical-model-selection.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2))
    temporary.replace(path)
    return payload
