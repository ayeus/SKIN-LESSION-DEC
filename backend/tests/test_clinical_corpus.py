"""Explicitly synthetic BRAT/math fixtures, never clinical observations."""

import json
from uuid import uuid4
import pytest
from backend.app.services.clinical_corpus import parse_brat, span_metrics
from backend.app.services.ner_training import document_split


def test_brat_offsets_discontinuity_and_uninterpreted_records():
    parsed = parse_brat(
        "rash and fever", "T1\tSign_symptom 0 4;9 14\trash fever\nA1\tPolarity T1 NEG"
    )
    assert parsed["entities"][0]["spans"] == [[0, 4], [9, 14]]
    assert parsed["uninterpreted_record_counts"] == {"A": 1}
    for annotation in [
        "T1\tDisease 0 99\trash",
        "T1\tDisease 0 4\twrong",
        "T1\tDisease 9 14;0 4\tfever rash",
    ]:
        with pytest.raises(ValueError):
            parse_brat("rash and fever", annotation)
    with pytest.raises(ValueError, match="duplicate"):
        parse_brat("rash", "T1\tSign 0 4\trash\nT1\tSign 0 4\trash")


def test_exact_spans_keep_overlap_in_recall_and_count_unsupported_gold():
    gold = [
        [
            {"label": "A", "spans": [[0, 4]]},
            {"label": "B", "spans": [[0, 2]]},
            {"label": "A", "spans": [[5, 6], [7, 8]]},
        ]
    ]
    result = span_metrics(
        gold,
        [[{"label": "A", "start": 0, "end": 4}, {"label": "B", "start": 1, "end": 2}]],
    )
    assert result["micro"]["precision"] == 0.5 and result["micro"]["recall"] == 0.5
    assert (
        result["micro"]["false_positive"] == 1
        and result["micro"]["false_negative"] == 1
    )
    assert result["excluded_discontinuous_mentions"] == 1


def test_document_split_is_reproducible_disjoint_and_blocks_identical_text():
    corpus = [{"document_id": str(i), "text": str(i)} for i in range(20)]
    split = document_split(corpus)
    assert split == document_split(list(reversed(corpus)))
    assert [len(split[k]) for k in ["train", "validation", "test"]] == [14, 3, 3]
    assert len(set(sum(split.values(), []))) == 20
    corpus[-1]["text"] = corpus[0]["text"]
    with pytest.raises(ValueError, match="leak"):
        document_split(corpus)


def test_actual_isolated_ner_training_selection_inference_and_checksum(
    tmp_path, monkeypatch
):
    pytest.importorskip(
        "spacy", reason="Optional clinical runtime; parser/scorer tests run without it"
    )
    from backend.app.services.ner_training import train
    from backend.app.db import ROOT
    from backend.app import clinical_training
    from backend.app.main import app, execute
    from backend.app.services.text import clinical_entities
    from fastapi.testclient import TestClient

    corpus = []
    for i in range(20):
        text = f"Example {i} reports rash."
        start = text.index("rash")
        corpus.append(
            {
                "document_id": str(i),
                "text": text,
                "entities": [
                    {
                        "label": "Sign_symptom",
                        "spans": [[start, start + 4]],
                        "text": "rash",
                    }
                ],
            }
        )
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(corpus))
    identifier = str(uuid4())
    artifact = ROOT / "nlp_models" / identifier
    report = train(path, artifact, epochs=1)
    assert report["test_metrics"]["micro"]["gold_mentions"] == 3
    assert len(json.loads((artifact / "history.json").read_text())) == 1
    with TestClient(app):
        run = execute(
            "clinical_ner_training",
            {},
            lambda rid: {"training_run_id": identifier, "evaluation": report},
        )
    token = {"Authorization": "Bearer synthetic-test-token-not-a-secret"}
    monkeypatch.delenv("DERMA_NER_MODEL", raising=False)
    pointer = ROOT / "clinical-model-selection.json"
    try:
        with TestClient(app) as client:
            assert (
                client.post("/clinical-models/select/" + run["id"]).status_code == 401
            )
            selected = client.post(
                "/clinical-models/select/" + run["id"], headers=token
            )
            assert selected.status_code == 200, selected.text
            assert (
                client.get("/clinical-models/current", headers=token).json()[
                    "model_card"
                ]["evaluation"]
                == report["test_metrics"]
            )
        result = clinical_entities(["Example 40 reports rash."])
        assert result["documents"][0]["text"] == "Example 40 reports rash."
        for entity in result["documents"][0]["entities"]:
            assert (
                result["documents"][0]["text"][entity["start"] : entity["end"]]
                == entity["text"]
            )
            assert entity["negated"] is None
        config = artifact / "pipeline/config.cfg"
        config.write_text(config.read_text() + "\n# mutation")
        with pytest.raises(ValueError, match="checksum"):
            clinical_training.validate_model(artifact / "pipeline")
    finally:
        pointer.unlink(missing_ok=True)
