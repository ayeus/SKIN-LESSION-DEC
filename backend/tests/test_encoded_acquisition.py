"""Real HTTP compressed-byte fixture, not a healthcare data source."""

import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from scripts import acquire_public_data as acquisition


def test_source_gzip_bytes_are_preserved_despite_http_content_encoding(
    tmp_path, monkeypatch
):
    body = gzip.compress(b"Explicit synthetic source fixture\n" * 100)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Encoding", "x-gzip")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(acquisition, "ROOT", tmp_path)
    try:
        path = acquisition.acquire(
            f"http://127.0.0.1:{server.server_port}/source.gz",
            tmp_path / "source.gz",
            "test only",
            "synthetic local HTTP fixture",
        )
        assert path.read_bytes() == body
        assert (
            gzip.decompress(path.read_bytes())
            == b"Explicit synthetic source fixture\n" * 100
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
