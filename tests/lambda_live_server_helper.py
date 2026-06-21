from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any


class LambdaLiveFakeServer:
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.responses = responses or _default_responses()
        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                path = self.path.removeprefix("/api/v1")
                if path not in server_ref.responses:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"{}")
                    return
                payload = server_ref.responses[path]
                status = 200
                if isinstance(payload, tuple):
                    status, payload = payload
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if isinstance(payload, bytes):
                    self.wfile.write(payload)
                else:
                    self.wfile.write(json.dumps(payload).encode("utf-8"))

            def do_POST(self) -> None:  # noqa: N802
                self.send_response(403)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                return

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/api/v1"

    def __enter__(self) -> LambdaLiveFakeServer:
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()


def _default_responses() -> dict[str, Any]:
    return {
        "/regions": [{"region_id": "us-west-1", "name": "US West", "available": True}],
        "/instance-types": [
            {
                "instance_type_id": "gpu_8x_h100_sxm",
                "name": "8x H100",
                "gpu_type": "H100 SXM",
                "gpus": 8,
                "regions": ["us-west-1"],
            }
        ],
        "/images": [{"image_id": "img-fixture", "name": "fixture"}],
        "/ssh-keys": [{"key_id": "key-fixture", "name": "fixture"}],
        "/file-systems": [{"filesystem_id": "fs-fixture", "name": "fixture"}],
        "/instances": [
            {
                "instance_id": "i-live-fixture",
                "name": "live-fixture",
                "status": "active",
                "tags": {},
            }
        ],
        "/quota": {"max_instances": 4, "max_gpus": 16, "running_instances": 1},
        "/usage": {"estimated_hourly_cost": 1.0, "running_instance_count": 1},
    }
