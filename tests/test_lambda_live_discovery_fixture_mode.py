import json
import subprocess
import sys

import pytest
from lambda_live_server_helper import LambdaLiveFakeServer

pytestmark = pytest.mark.integration


def test_lambda_live_discover_cli_against_local_fake_server(tmp_path) -> None:
    key = tmp_path / "lambda_key.txt"
    key.write_text("fixture-readonly-key", encoding="utf-8")
    key.chmod(0o600)
    out = tmp_path / "lambda-live-discovery.json"

    with LambdaLiveFakeServer() as server:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "decodilo.cli",
                "lambda",
                "live-discover",
                "--api-key-file",
                str(key),
                "--live-read-only",
                "--base-url",
                server.base_url,
                "--out",
                str(out),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

    summary = json.loads(result.stdout)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert summary["live_api_used"] is True
    assert summary["mutating_operations"] == 0
    assert report["billable_action_performed"] is False
    assert "fixture-readonly-key" not in out.read_text(encoding="utf-8")


def test_lambda_live_discovery_partial_endpoint_failure_recorded() -> None:
    from decodilo.lambda_cloud.live_discovery import run_lambda_live_discovery
    from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient
    from decodilo.lambda_cloud.real_read_only_transport import (
        LambdaHTTPResponse,
        RealReadOnlyLambdaTransport,
        RealReadOnlyTransportConfig,
    )

    def getter(request, timeout):  # noqa: ANN001
        if request.full_url.endswith("/images"):
            return LambdaHTTPResponse(500, b"{}")
        return LambdaHTTPResponse(200, b"[]")

    transport = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(live_read_only=True),
        http_getter=getter,
    )

    report = run_lambda_live_discovery(LiveReadOnlyLambdaCloudClient(transport))

    assert report.errors
    assert report.billable_action_performed is False
