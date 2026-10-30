"""Isolated nonclinical lexical fixtures verify ranking, privacy and retention."""

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from backend.app.services.terminology import contextual_candidates
from backend.app.db import Session, Run
from backend.app.main import app

TOKEN = {"Authorization": "Bearer synthetic-test-token-not-a-secret"}


@pytest.fixture
def inventory(tmp_path, monkeypatch):
    payload = {
        "metadata": {
            "source": "https://example.test/synthetic-lexicon",
            "attribution": "Explicit synthetic nonclinical test inventory",
            "version": "fixture-only",
            "limitations": "Algorithm-verification fixture, not medical concepts.",
        },
        "records": [
            {
                "id": "fixture-river",
                "label": "river bank",
                "definition": "river water shore sediment channel",
                "entry_terms": ["bank"],
            },
            {
                "id": "fixture-finance",
                "label": "financial bank",
                "definition": "deposit account savings banking money",
                "entry_terms": ["financial bank"],
            },
        ],
        "index": {"bank": [0], "financial bank": [1]},
    }
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(payload))
    monkeypatch.setenv("DERMA_MESH_INVENTORY", str(path))
    return path


def test_context_changes_ranking_without_fixed_sense_mapping_and_unknown_stays_unresolved(
    inventory,
):
    river = contextual_candidates("bank", "water river shore sediment")
    finance = contextual_candidates("bank", "savings money deposit account")
    assert (
        river["candidate_count"] == 2
        and river["sense_candidates"][0]["id"] == "fixture-river"
    )
    assert finance["sense_candidates"][0]["id"] == "fixture-finance"
    assert river["context_sent_to_external_service"] is False
    assert river["sense_candidates"][0]["shared_context_terms"]
    missing = contextual_candidates(
        "unknown-abbreviation", "some actual supplied context"
    )
    assert missing["status"] == "unresolved" and not missing["sense_candidates"]
    no_overlap = contextual_candidates("bank", "unrelated zzzzz yyyyy")
    assert no_overlap["status"] == "unresolved" and all(
        c["context_similarity"] == 0 for c in no_overlap["sense_candidates"]
    )


def test_real_api_protects_context_and_retains_only_when_requested(inventory):
    with TestClient(app) as client:
        assert client.get("/terminology/status").status_code == 401
        assert (
            client.get("/terminology/status", headers=TOKEN).json()[
                "descriptor_records"
            ]
            == 2
        )
        with Session() as session:
            before = session.scalar(
                select(func.count()).select_from(Run).where(Run.kind == "terminology")
            )
        response = client.post(
            "/terminology/disambiguate",
            headers=TOKEN,
            json={"term": "bank", "context": "river water shore"},
        )
        assert response.status_code == 200 and response.json()["retained"] is False
        with Session() as session:
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(Run)
                    .where(Run.kind == "terminology")
                )
                == before
            )
        retained = client.post(
            "/terminology/disambiguate",
            headers=TOKEN,
            json={"term": "bank", "context": "river water shore", "retain": True},
        )
        assert retained.status_code == 200 and retained.json()["status"] == "completed"
        assert (
            client.get("/runs/" + retained.json()["id"], headers=TOKEN).json()[
                "result"
            ]["sense_candidates"][0]["id"]
            == "fixture-river"
        )
        bad = client.post(
            "/terminology/disambiguate",
            headers=TOKEN,
            json={"term": "bank", "context": "x" * 10001},
        )
        assert bad.status_code == 422 and "x" * 100 not in bad.text


def test_missing_inventory_cannot_produce_a_fallback_sense(tmp_path, monkeypatch):
    monkeypatch.setenv("DERMA_MESH_INVENTORY", str(tmp_path / "absent.json"))
    with pytest.raises(ValueError, match="BLOCKED"):
        contextual_candidates("bank", "river water shore")
