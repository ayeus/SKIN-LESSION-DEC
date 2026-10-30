import io
import json
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app

H = {"Authorization": "Bearer synthetic-test-token-not-a-secret"}


def test_auth_import_transform_export_persistence():
    with TestClient(app) as client:
        assert client.get("/status").status_code == 401
        raw = b"Patient,Encounter,Value\n1,10,2\n1,11,4\n1,11,4\n"
        data = {
            "modality": "ehr",
            "source": "explicit synthetic unit test",
            "license": "test-only",
            "authorized": "true",
        }
        imported = client.post(
            "/datasets",
            headers=H,
            data=data,
            files={"file": ("fixture.csv", raw, "text/csv")},
        )
        assert imported.status_code == 200, imported.text
        id = imported.json()["id"]
        assert imported.json()["profile"]["rows"] == 3
        run = client.post(
            "/analyze/preprocess",
            headers=H,
            json={"dataset_id": id, "parameters": {"drop_exact_duplicates": True}},
        )
        assert run.status_code == 200, run.text
        rid = run.json()["id"]
        assert run.json()["result"]["after"]["rows"] == 2
        assert client.get("/runs/" + rid, headers=H).json()["status"] == "completed"
        exported = client.get(f"/runs/{rid}/export/csv", headers=H)
        assert exported.status_code == 200
        assert "patient,encounter,value" in exported.text
        assert client.get("/datasets/" + id, headers=H).json()["profile"]["rows"] == 3
        assert (
            client.post(
                "/analyze/forecast", headers=H, json={"dataset_id": id}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/inference", headers=H, files={"file": ("x.png", b"bad")}
            ).status_code
            == 409
        )
        assert client.get("/runs/not-an-id/export/json", headers=H).status_code == 404


def test_image_api_and_failure_is_persisted():
    image = Image.fromarray(np.full((32, 32, 3), 120, np.uint8))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    with TestClient(app) as client:
        result = client.post(
            "/images/process",
            headers=H,
            data={"method": "png", "parameters": "{}"},
            files={"file": ("synthetic.png", stream.getvalue(), "image/png")},
        )
        assert result.status_code == 200, result.text
        assert result.json()["result"]["metrics"]["lossless"]
        bad = client.post(
            "/images/process",
            headers=H,
            data={"method": "nonexistent"},
            files={"file": ("synthetic.png", stream.getvalue(), "image/png")},
        )
        assert bad.status_code == 422
        assert any(
            r["status"] == "failed" for r in client.get("/runs", headers=H).json()
        )
        assert (
            client.post(
                "/images/process",
                headers=H,
                data={"method": "png"},
                files={"file": ("bad.png", b"bad")},
            ).status_code
            == 422
        )


def test_import_requires_authorization_and_provenance():
    with TestClient(app) as client:
        r = client.post(
            "/datasets",
            headers=H,
            data={
                "modality": "ehr",
                "source": "fixture",
                "license": "test",
                "authorized": "false",
            },
            files={"file": ("x.csv", b"a\n1")},
        )
        assert r.status_code == 422


def test_background_run_reaches_persisted_terminal_state():
    import time

    with TestClient(app) as client:
        data = {
            "modality": "tabular",
            "source": "synthetic job test",
            "license": "test",
            "authorized": "true",
        }
        id = client.post(
            "/datasets",
            headers=H,
            data=data,
            files={"file": ("synthetic.csv", b"x,z\n1,2\n2,4\n3,6\n4,8")},
        ).json()["id"]
        job = client.post(
            "/analyze/reduce?background=true",
            headers=H,
            json={"dataset_id": id, "parameters": {"features": ["x", "z"]}},
        )
        assert job.status_code == 200, job.text
        for _ in range(100):
            run = client.get("/runs/" + job.json()["id"], headers=H).json()
            if run["status"] in ("completed", "failed"):
                break
            time.sleep(0.02)
        assert run["status"] == "completed", run
        assert len(run["result"]["coordinates"]) == 4


def test_analysis_report_keeps_source_provenance_and_scope():
    from backend.app.db import Dataset, Session

    with TestClient(app) as client:
        response = client.post(
            "/datasets",
            headers=H,
            data={
                "modality": "tabular",
                "source": "isolated scoped fixture",
                "license": "test-only",
                "authorized": "true",
            },
            files={"file": ("fixture.csv", b"x,y\n1,2\n3,4")},
        )
        id = response.json()["id"]
        with Session() as session:
            dataset = session.get(Dataset, id)
            dataset.profile = {
                **dataset.profile,
                "research_scope": {"limitations": "Isolated source scope fixture"},
            }
            session.commit()
        result = client.post(
            "/analyze/overview", headers=H, json={"dataset_id": id}
        ).json()["result"]
        assert result["dataset_provenance"]["id"] == id
        assert result["dataset_provenance"]["source"] == "isolated scoped fixture"
        assert len(result["dataset_provenance"]["sha256"]) == 64
        assert "path" not in result["dataset_provenance"]
        assert result["data_scope"]["limitations"] == "Isolated source scope fixture"


def test_three_dimensional_analysis_persists_actual_coordinates_and_source():
    """Isolated numeric geometry fixture; never a clinical dataset."""
    with TestClient(app) as client:
        imported = client.post(
            "/datasets",
            headers=H,
            data={
                "modality": "weight",
                "source": "synthetic geometric test",
                "license": "test-only",
                "authorized": "true",
            },
            files={
                "file": (
                    "geometry.csv",
                    b"a,b,c\n0,0,0\n1,2,-1\n2,4,-2\n3,6,-3\n4,8,-4\n",
                    "text/csv",
                )
            },
        )
        assert imported.status_code == 200, imported.text
        dataset_id = imported.json()["id"]
        response = client.post(
            "/analyze/reduce",
            headers=H,
            json={
                "dataset_id": dataset_id,
                "parameters": {"features": ["a", "b", "c"], "dimensions": 3},
            },
        )
        assert response.status_code == 200, response.text
        run = response.json()
        coordinates = np.asarray(run["result"]["coordinates"])
        assert coordinates.shape == (5, 3) and np.isfinite(coordinates).all()
        assert run["result"]["dataset_provenance"]["id"] == dataset_id
        exported = client.get(f"/runs/{run['id']}/export/json", headers=H)
        assert exported.status_code == 200
        assert exported.json()["coordinates"] == run["result"]["coordinates"]


def test_planning_route_uses_explicit_scenarios_and_never_invents_staff_availability():
    """Constant mathematical count fixture, not hospital observations."""
    import pandas as pd

    frame = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=28).strftime("%Y-%m-%d"),
            "count": [8] * 28,
        }
    )
    with TestClient(app) as client:
        imported = client.post(
            "/datasets",
            headers=H,
            data={
                "modality": "demand",
                "source": "Explicit synthetic mathematical test",
                "license": "isolated test only",
                "authorized": "true",
            },
            files={
                "file": (
                    "synthetic-counts.csv",
                    frame.to_csv(index=False).encode(),
                    "text/csv",
                )
            },
        )
        assert imported.status_code == 200, imported.text
        response = client.post(
            "/analyze/planning",
            headers=H,
            json={
                "dataset_id": imported.json()["id"],
                "parameters": {
                    "horizon": 2,
                    "scenarios": [
                        {"name": "test assumption", "patients_per_staff_per_shift": 4}
                    ],
                },
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()["result"]
        assert len(result["forecast"]) == 2
        assert result["planning_scenarios"][0]["required_staff_shifts_per_day"] == [
            2,
            2,
        ]
        assert (
            result["planning_scenarios"][0]["summary"][
                "maximum_shift_workload_shortfall"
            ]
            is None
        )
        assert result["dataset_provenance"]["id"] == imported.json()["id"]
