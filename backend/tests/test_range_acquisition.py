"""Real local HTTP/range I/O on an explicitly synthetic ZIP, not clinical data."""

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import re
from threading import Thread
from zipfile import ZipFile
import numpy as np
import pytest
from scripts.resume_public_archive import download, fetch_range


@pytest.fixture
def source():
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr(
            "synthetic.bin",
            np.random.default_rng(42).integers(0, 256, 40000, dtype=np.uint8).tobytes(),
        )
    payload = stream.getvalue()
    state = {"bad_range": False, "requests": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("ETag", '"fixture-v1"')
            self.end_headers()

        def do_GET(self):
            assert self.headers["If-Match"] == '"fixture-v1"'
            match = re.fullmatch(r"bytes=(\d+)-(\d+)", self.headers["Range"])
            start, end = map(int, match.groups())
            state["requests"].append((start, end))
            content = payload[start : end + 1]
            self.send_response(206)
            self.send_header(
                "Content-Range",
                f"bytes {start + int(state['bad_range'])}-{end}/{len(payload)}",
            )
            self.send_header("Content-Length", str(len(content)))
            self.send_header("ETag", '"fixture-v1"')
            self.end_headers()
            self.wfile.write(content)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/source", payload, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_parallel_resume_preserves_prefix_validates_zip_and_records_real_digest(
    source, tmp_path
):
    url, payload, state = source
    destination = tmp_path / "source.zip"
    destination.with_suffix(".zip.part").write_bytes(payload[:10000])
    (tmp_path / "archive-resource.json").write_text(
        json.dumps({"url": url, "etag": '"fixture-v1"', "expected_bytes": len(payload)})
    )
    result = download(
        url, destination, "synthetic test only", workers=3, chunk_bytes=8192
    )
    assert result.read_bytes() == payload
    receipt = json.loads(destination.with_suffix(".zip.provenance.json").read_text())
    assert (
        receipt["sha256"] == hashlib.sha256(payload).hexdigest()
        and receipt["zip_crc_verified"]
    )
    assert receipt["publisher_checksum_verified"] is False
    assert min(start for start, end in state["requests"]) == 10000
    assert not destination.with_suffix(".zip.part").exists()


def test_range_mismatch_and_cache_tamper_are_rejected(source, tmp_path):
    url, payload, state = source
    path = tmp_path / "range.bin"
    state["bad_range"] = True
    with pytest.raises(ValueError, match="inconsistent range"):
        fetch_range(url, path, 0, 100, len(payload), '"fixture-v1"')
    assert not path.exists()
    state["bad_range"] = False
    fetch_range(url, path, 0, 100, len(payload), '"fixture-v1"')
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Cached range changed"):
        fetch_range(url, path, 0, 100, len(payload), '"fixture-v1"')
