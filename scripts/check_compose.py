"""Disposable full-stack Compose integration check. Fixtures are synthetic and isolated."""

import json
import os
import secrets
import socket
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def check():
    for port in (3000, 8000):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as error:
                raise RuntimeError(
                    f"Local port {port} is occupied; stop only your intended preview before this check"
                ) from error
    project = "dermacheck" + uuid4().hex[:10]
    command = ["docker", "compose", "-p", project]
    env = os.environ.copy()
    env["POSTGRES_PASSWORD"] = secrets.token_urlsafe(24)
    env["DERMA_API_TOKEN"] = secrets.token_urlsafe(32)

    def request(
        path, method="GET", payload=None, token=None, content_type="application/json"
    ):
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        if payload is not None:
            headers["Content-Type"] = content_type
        req = Request(
            "http://127.0.0.1:3000" + path,
            method=method,
            headers=headers,
            data=(
                payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            )
            if payload is not None
            else None,
        )
        with urlopen(req, timeout=20) as response:
            data = response.read()
            return response.status, json.loads(
                data
            ) if response.headers.get_content_type() == "application/json" else data

    try:
        subprocess.run(
            command + ["up", "--build", "-d", "--wait", "--wait-timeout", "120"],
            env=env,
            check=True,
        )
        for _ in range(90):
            try:
                if request("/api/health")[0] == 200:
                    break
            except (HTTPError, URLError, TimeoutError):
                time.sleep(1)
        else:
            raise RuntimeError("Frontend-to-API proxy did not become ready")
        assert request("/")[0] == 200
        try:
            request("/api/status")
            raise AssertionError("Unauthenticated status unexpectedly allowed")
        except HTTPError as error:
            assert error.code == 401
        token = env["DERMA_API_TOKEN"]
        status = request("/api/status", token=token)[1]
        assert status["datasets"] == 0 and status["model_available"] is False
        code, user = request(
            "/api/auth/users",
            "POST",
            {
                "username": "isolated_compose_fixture",
                "password": secrets.token_urlsafe(24),
                "role": "viewer",
            },
            token,
        )
        assert code == 201 and user["role"] == "viewer"
        assert request("/api/auth/users", token=token)[1][0]["id"] == user["id"]
        try:
            request("/api/training", "POST", {}, token)
            raise AssertionError("Training without images unexpectedly started")
        except HTTPError as error:
            assert error.code == 409
        assert request("/api/training/readiness", token=token)[1]["ready"] is False
        # Exercise actual pixels -> algorithm -> persisted filesystem report through the web proxy.
        import io
        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (32, 32), (120, 120, 120)).save(buffer, format="PNG")
        boundary = "fixture" + uuid4().hex
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="method"\r\n\r\npng\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="isolated-synthetic.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
            + buffer.getvalue()
            + f"\r\n--{boundary}--\r\n".encode()
        )
        _, run = request(
            "/api/images/process",
            "POST",
            body,
            token,
            "multipart/form-data; boundary=" + boundary,
        )
        assert run["result"]["metrics"]["lossless"] is True
        assert run["result"]["metrics"]["ssim"] == 1
        _, exported = request("/api/runs/" + run["id"] + "/export/json", token=token)
        if isinstance(exported, bytes):
            exported = json.loads(exported)
        assert exported["metrics"]["lossless"] is True
        # Base container intentionally lacks optional torch. A synthetic manifest must
        # produce a dependency blocker, never an invented model or internal-server success.
        fixture = "from pathlib import Path; p=Path('/app/data/raw/isic2018-task3'); p.mkdir(parents=True,exist_ok=True); (p/'metadata.csv').write_bytes(bytes.fromhex('696d6167655f706174682c6c6162656c2c67726f75705f69640a612e706e672c612c610a'))"
        subprocess.run(
            command + ["exec", "-T", "api", "python", "-c", fixture],
            env=env,
            check=True,
        )
        ready = request("/api/training/readiness", token=token)[1]
        assert ready["ready"] is False and "CNN runtime" in ready["reason"]
        print(
            "Full-stack Compose check passed: PostgreSQL migration, API authentication/account persistence, frontend HTTP/proxy, real image processing/export and missing-model/runtime gates. Only isolated synthetic fixtures created.",
            flush=True,
        )
    finally:
        subprocess.run(
            command + ["down", "--volumes", "--remove-orphans"], env=env, check=True
        )


if __name__ == "__main__":
    check()
