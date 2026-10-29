"""Isolated user/session/ownership verification; no real credentials or patient data."""

import hashlib
import time
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.app.main import app
from backend.app.db import Session, User, AccessSession, Audit
from backend.app.auth import hash_password, verify_password

ADMIN = {"Authorization": "Bearer synthetic-test-token-not-a-secret"}
PASSWORD = "isolated-test-password-123"


def create(client, role="researcher"):
    username = "test_" + uuid4().hex[:12]
    response = client.post(
        "/auth/users",
        headers=ADMIN,
        json={"username": username, "password": PASSWORD, "role": role},
    )
    assert response.status_code == 201, response.text
    login = client.post(
        "/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    return response.json(), {"Authorization": "Bearer " + login.json()["access_token"]}


def upload(client, headers):
    response = client.post(
        "/datasets",
        headers=headers,
        data={
            "source": "synthetic ownership fixture",
            "license": "test only",
            "modality": "ehr",
            "authorized": "true",
        },
        files={"file": ("fixture.csv", b"id,value\n1,10\n2,20")},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_passwords_are_salted_and_verified():
    a = hash_password(PASSWORD)
    b = hash_password(PASSWORD)
    assert a != b and PASSWORD not in a and verify_password(PASSWORD, a)
    assert not verify_password("wrong", a)


def test_role_scope_grants_revoke_and_private_artifacts():
    with TestClient(app) as client:
        alice, ha = create(client)
        bob, hb = create(client)
        viewer, hv = create(client, "viewer")
        id = upload(client, ha)
        assert client.get("/datasets/" + id, headers=hb).status_code == 404
        assert client.get("/datasets/" + id + "/rows", headers=hb).status_code == 404
        assert id not in [d["id"] for d in client.get("/datasets", headers=hb).json()]
        assert client.get("/status", headers=hb).json()["datasets"] == 0
        assert (
            client.post(
                "/datasets",
                headers=hv,
                data={
                    "source": "test",
                    "license": "test",
                    "modality": "ehr",
                    "authorized": "true",
                },
                files={"file": ("x.csv", b"x\n1")},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/auth/users",
                headers=ha,
                json={"username": "notallowed", "password": PASSWORD},
            ).status_code
            == 403
        )
        assert client.post("/training", headers=ha, json={}).status_code == 403
        assert (
            client.post(
                "/datasets/" + id + "/grants",
                headers=hb,
                json={"user_id": viewer["id"]},
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/datasets/" + id + "/grants",
                headers=ha,
                json={"user_id": viewer["id"]},
            ).status_code
            == 200
        )
        assert client.get("/datasets/" + id + "/rows", headers=hv).status_code == 200
        assert (
            client.post(
                "/analyze/preprocess", headers=hv, json={"dataset_id": id}
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/datasets/" + id + "/grants", headers=hv, json={"user_id": bob["id"]}
            ).status_code
            == 403
        )
        grant = client.post(
            "/datasets/" + id + "/grants", headers=ha, json={"user_id": bob["id"]}
        )
        assert grant.status_code == 200
        run = client.post("/analyze/preprocess", headers=hb, json={"dataset_id": id})
        assert run.status_code == 200, run.text
        rid = run.json()["id"]
        assert client.get("/runs/" + rid, headers=hb).status_code == 200
        assert (
            client.get("/runs/" + rid, headers=ha).status_code == 404
        )  # Dataset owner does not own another user's analysis.
        assert (
            client.get("/runs/" + rid + "/export/json", headers=ha).status_code == 404
        )
        assert (
            client.delete(
                "/datasets/" + id + "/grants/" + bob["id"], headers=ha
            ).status_code
            == 200
        )
        assert client.get("/runs/" + rid, headers=hb).status_code == 404
        assert (
            client.get("/runs/" + rid + "/export/json", headers=hb).status_code == 404
        )
        assert client.get("/runs/" + rid, headers=ADMIN).status_code == 200
        with Session() as s:
            actor = s.scalar(
                select(Audit).where(
                    Audit.resource_id == id, Audit.action == "dataset_import"
                )
            )
            assert actor.actor_id == alice["id"]


def test_session_expiration_logout_hashing_and_disabled_users():
    with TestClient(app) as client:
        user, headers = create(client)
        token = headers["Authorization"].split()[1]
        with Session() as s:
            session = s.get(AccessSession, hashlib.sha256(token.encode()).hexdigest())
            assert session and session.token_hash != token
            session.expires_at = int(time.time()) - 1
            s.commit()
        assert client.get("/auth/me", headers=headers).status_code == 401
        login = client.post(
            "/auth/login", json={"username": user["username"], "password": PASSWORD}
        ).json()
        h = {"Authorization": "Bearer " + login["access_token"]}
        assert client.post("/auth/logout", headers=h).json()["session_revoked"]
        assert client.get("/auth/me", headers=h).status_code == 401
        login = client.post(
            "/auth/login", json={"username": user["username"], "password": PASSWORD}
        ).json()
        h = {"Authorization": "Bearer " + login["access_token"]}
        assert (
            client.patch(
                "/auth/users/" + user["id"], headers=ADMIN, json={"active": False}
            ).status_code
            == 200
        )
        assert client.get("/auth/me", headers=h).status_code == 401
        assert (
            client.post(
                "/auth/login", json={"username": user["username"], "password": PASSWORD}
            ).status_code
            == 401
        )
        assert "password_hash" not in client.get("/auth/users", headers=ADMIN).text


def test_login_throttle_and_no_public_signup(monkeypatch):
    with TestClient(app) as client:
        user, headers = create(client)
        for _ in range(5):
            response = client.post(
                "/auth/login", json={"username": user["username"], "password": "wrong"}
            )
            assert response.status_code == 401
        response = client.post(
            "/auth/login", json={"username": user["username"], "password": PASSWORD}
        )
        assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0
        assert (
            client.post(
                "/auth/users", json={"username": "public_signup", "password": PASSWORD}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/auth/users",
                headers=ADMIN,
                json={"username": "shortpass", "password": "tiny"},
            ).status_code
            == 422
        )


def test_validation_never_echoes_password_input():
    with TestClient(app) as client:
        response = client.post(
            "/auth/users",
            headers=ADMIN,
            json={"username": "short_fixture", "password": "tiny"},
        )
        assert response.status_code == 422
        assert "tiny" not in response.text and all(
            "input" not in v for v in response.json()["detail"]
        )


def test_audit_visibility_is_admin_only_and_records_no_credentials():
    with TestClient(app) as client:
        user, headers = create(client)
        assert client.get("/audit", headers=headers).status_code == 403
        assert (
            client.get("/audit", headers=ADMIN, params={"limit": 201}).status_code
            == 422
        )
        response = client.get(
            "/audit", headers=ADMIN, params={"action": "login_success", "limit": 100}
        )
        assert response.status_code == 200
        events = response.json()
        assert any(item["actor_id"] == user["id"] for item in events)
        assert all(item["action"] == "login_success" for item in events)
        assert PASSWORD not in response.text and "token_hash" not in response.text
