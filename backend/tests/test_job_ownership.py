"""Lifecycle recovery must not falsely fail a separately running CLI experiment."""

import os
import socket
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app.db import Session, Run, Base, engine
from backend.app.main import app


def test_startup_recovers_only_known_dead_api_processes():
    Base.metadata.create_all(engine)
    rows = []
    for owner in [
        {"kind": "api", "pid": 999999999, "host": socket.gethostname()},
        {"kind": "cli", "pid": 999999999, "host": socket.gethostname()},
        {"kind": "api", "pid": os.getpid(), "host": socket.gethostname()},
        None,
    ]:
        rows.append(
            Run(
                id=str(uuid4()),
                kind="explicit-lifecycle-test",
                status="running",
                parameters={"_execution": owner} if owner else {},
                result={},
            )
        )
    with Session() as session:
        session.add_all(rows)
        session.commit()
    try:
        with TestClient(app):
            with Session() as session:
                states = [session.get(Run, row.id).status for row in rows]
            assert states == ["failed", "running", "running", "running"]
    finally:
        with Session() as session:
            for row in rows:
                session.delete(session.get(Run, row.id))
            session.commit()
