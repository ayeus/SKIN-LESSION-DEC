"""Disposable PostgreSQL migration/API verification; never touches an existing database."""

import os
import secrets
import subprocess
import sys
import time
from uuid import uuid4


def check():
    name = "derma-check-" + uuid4().hex[:12]
    env = os.environ.copy()
    env["POSTGRES_PASSWORD"] = secrets.token_urlsafe(24)
    started = False
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "--name",
                name,
                "--env",
                "POSTGRES_PASSWORD",
                "--env",
                "POSTGRES_USER=derma",
                "--env",
                "POSTGRES_DB=dermatest",
                "--tmpfs",
                "/var/lib/postgresql/data:rw",
                "-p",
                "127.0.0.1::5432",
                "postgres:17-alpine",
            ],
            env=env,
            check=True,
            capture_output=True,
        )
        started = True
        for _ in range(60):
            ready = subprocess.run(
                [
                    "docker",
                    "exec",
                    name,
                    "pg_isready",
                    "-U",
                    "derma",
                    "-d",
                    "dermatest",
                ],
                capture_output=True,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Disposable PostgreSQL did not become ready")
        mapping = subprocess.check_output(
            ["docker", "port", name, "5432/tcp"], text=True
        ).strip()
        port = int(mapping.rsplit(":", 1)[1])
        env["DATABASE_URL"] = (
            f"postgresql+psycopg2://derma:{env['POSTGRES_PASSWORD']}@127.0.0.1:{port}/dermatest"
        )
        env["DERMA_STORAGE"] = "/private/tmp/" + name
        subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "backend/alembic.ini",
                "upgrade",
                "head",
            ],
            env=env,
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "backend/tests/test_api.py",
                "backend/tests/test_fhir.py",
                "backend/tests/test_training_api.py",
                "backend/tests/test_relationships.py",
                "backend/tests/test_identity.py",
                "-q",
            ],
            env=env,
            check=True,
        )
        print(
            "Disposable PostgreSQL migrations and API/FHIR/training tests passed; container will be removed.",
            flush=True,
        )
    finally:
        if started:
            subprocess.run(
                ["docker", "stop", "--time", "5", name], check=True, capture_output=True
            )


if __name__ == "__main__":
    check()
