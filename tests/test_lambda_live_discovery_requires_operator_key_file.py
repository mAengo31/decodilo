import json
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def test_lambda_live_discover_rejects_raw_api_key_argument(tmp_path) -> None:
    out = tmp_path / "out.json"
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
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode != 0
    assert "lambda_12345678901234567890" not in result.stdout
    assert "lambda_12345678901234567890" not in result.stderr


def test_lambda_live_discover_writes_summary_with_fake_base_url(tmp_path) -> None:
    from lambda_live_server_helper import LambdaLiveFakeServer

    key = tmp_path / "lambda_key.txt"
    key.write_text("fixture-readonly-key", encoding="utf-8")
    key.chmod(0o600)
    out = tmp_path / "discovery.json"
    summary_out = tmp_path / "summary.json"

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
                "--endpoint-set",
                "minimal",
                "--max-pages",
                "10",
                "--max-items",
                "1000",
                "--summary-out",
                str(summary_out),
                "--redaction-mode",
                "public_summary",
                "--out",
                str(out),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

    payload = json.loads(result.stdout)
    summary = json.loads(summary_out.read_text(encoding="utf-8"))
    assert payload["endpoint_count_attempted"] == 2
    assert summary["redaction_mode"] == "public_summary"
    assert "fixture-readonly-key" not in out.read_text(encoding="utf-8")
    assert "fixture-readonly-key" not in summary_out.read_text(encoding="utf-8")


def test_lambda_live_discover_accepts_explicit_env_file_source(tmp_path) -> None:
    from lambda_live_server_helper import LambdaLiveFakeServer

    secret = "fixture-env-readonly-key"
    env_file = tmp_path / ".env"
    env_file.write_text(f"LAMBDA_API_KEY={secret}\n", encoding="utf-8")
    out = tmp_path / "discovery.json"

    with LambdaLiveFakeServer() as server:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "decodilo.cli",
                "lambda",
                "live-discover",
                "--env-file",
                str(env_file),
                "--env-key",
                "LAMBDA_API_KEY",
                "--live-read-only",
                "--base-url",
                server.base_url,
                "--endpoint-set",
                "minimal",
                "--out",
                str(out),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

    payload = json.loads(result.stdout)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert payload["secret_source"] == "env_file"
    assert payload["secret_loaded"] is True
    assert report["secret_source"] == "env_file"
    assert report["env_file_basename"] == ".env"
    assert secret not in out.read_text(encoding="utf-8")


def test_lambda_live_discover_rejects_multiple_secret_sources(tmp_path) -> None:
    key = tmp_path / "lambda_key.txt"
    key.write_text("fixture-readonly-key", encoding="utf-8")
    key.chmod(0o600)
    env_file = tmp_path / ".env"
    env_file.write_text("LAMBDA_API_KEY=fixture-env-key\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "live-discover",
            "--api-key-file",
            str(key),
            "--env-file",
            str(env_file),
            "--live-read-only",
            "--out",
            str(tmp_path / "out.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 1
    assert "exactly one secret source" in result.stdout
