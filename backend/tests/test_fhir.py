"""Synthetic FHIR resources for structural verification, never clinical data."""

import json
import pytest
from fastapi.testclient import TestClient
from backend.app.services.fhir import parse
from backend.app.main import app
from backend.app.db import ROOT

H = {"Authorization": "Bearer synthetic-test-token-not-a-secret"}


def bundle():
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "p1", "gender": "unknown"}},
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "e1",
                    "status": "finished",
                    "subject": {"reference": "Patient/p1"},
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "o1",
                    "status": "final",
                    "subject": {"reference": "Patient/p1"},
                    "encounter": {"reference": "Encounter/e1"},
                    "code": {
                        "coding": [
                            {"system": "urn:test-only", "code": "synthetic-measurement"}
                        ]
                    },
                    "valueQuantity": {"value": 5, "unit": "test-unit"},
                    "effectiveDateTime": "2020-01-01T12:00:00Z",
                }
            },
        ],
    }


def test_linked_resources_and_exact_numeric_quantity():
    frame = parse(json.dumps(bundle()))
    assert len(frame) == 3
    observation = frame.loc[frame.resource_type == "Observation"].iloc[0]
    assert (
        observation.subject_id == "p1"
        and observation.encounter_id == "e1"
        and observation.value == 5
    )


def test_mixed_patient_reference_rejected():
    b = bundle()
    b["entry"].append({"resource": {"resourceType": "Patient", "id": "p2"}})
    b["entry"][2]["resource"]["subject"]["reference"] = "Patient/p2"
    with pytest.raises(ValueError, match="different patients"):
        parse(json.dumps(b))


@pytest.mark.parametrize(
    "change", ["name", "duplicate", "unknown_reference", "nan", "timezone"]
)
def test_invalid_or_identifying_resource_rejected(change):
    b = bundle()
    if change == "name":
        b["entry"][0]["resource"]["name"] = [{"family": "FORBIDDEN-SYNTHETIC-NAME"}]
    if change == "duplicate":
        b["entry"].append(b["entry"][0])
    if change == "unknown_reference":
        b["entry"][1]["resource"]["subject"]["reference"] = "Patient/absent"
    if change == "nan":
        b["entry"][2]["resource"]["valueQuantity"]["value"] = float("nan")
    if change == "timezone":
        b["entry"][2]["resource"]["effectiveDateTime"] = "2020-01-01T12:00:00"
    with pytest.raises(ValueError):
        parse(json.dumps(b))


def test_import_rejects_identifiers_before_disk_and_does_not_echo_values():
    b = bundle()
    b["entry"][0]["resource"]["name"] = [{"family": "FORBIDDEN-SYNTHETIC-NAME"}]
    before = set((ROOT / "raw").rglob("*")) if (ROOT / "raw").exists() else set()
    with TestClient(app) as client:
        response = client.post(
            "/datasets",
            headers=H,
            data={
                "modality": "ehr",
                "source": "synthetic test",
                "license": "test-only",
                "authorized": "true",
            },
            files={"file": ("test.json", json.dumps(b), "application/json")},
        )
        assert (
            response.status_code == 422
            and "FORBIDDEN-SYNTHETIC-NAME" not in response.text
        )
        assert set((ROOT / "raw").rglob("*")) == before
        valid = client.post(
            "/datasets",
            headers=H,
            data={
                "modality": "ehr",
                "source": "synthetic test",
                "license": "test-only",
                "authorized": "true",
            },
            files={"file": ("test.json", json.dumps(bundle()), "application/json")},
        )
        assert valid.status_code == 200, valid.text
        assert valid.json()["profile"]["rows"] == 3
