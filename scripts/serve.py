"""Start the local API with a safely parsed, ignored .env; never execute its contents."""

import argparse
import os
from pathlib import Path
import re


def local_environment(path=Path(".env")):
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not separator or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
            raise ValueError("Local .env must contain plain KEY=value assignments")
        if value[:1] in ['"', "'"] and value[-1:] == value[:1]:
            value = value[1:-1]
        os.environ.setdefault(key, value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    local_environment()
    if len(os.getenv("DERMA_API_TOKEN", "")) < 24:
        raise SystemExit(
            "Set DERMA_API_TOKEN in the ignored local .env or environment before starting the API"
        )
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=args.port)
