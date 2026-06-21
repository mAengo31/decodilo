import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def test_lambda_cli_rejects_raw_api_key_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "live-discover",
            "--api-key",
            "lambda_12345678901234567890",
            "--live-read-only",
            "--out",
            "/tmp/should-not-exist.json",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode != 0
    assert "--api-key-file" in result.stderr
    assert "lambda_12345678901234567890" not in result.stdout
