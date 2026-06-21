import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def test_lambda_live_discover_requires_explicit_live_opt_in(tmp_path) -> None:
    key = tmp_path / "lambda_key.txt"
    key.write_text("fixture-readonly-key", encoding="utf-8")
    key.chmod(0o600)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "live-discover",
            "--api-key-file",
            str(key),
            "--base-url",
            "http://127.0.0.1:9/api/v1",
            "--out",
            str(tmp_path / "out.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert "requires --live-read-only" in result.stdout
