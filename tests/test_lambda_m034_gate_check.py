import json
import subprocess
import sys

from lambda_m029_helpers import m029_fixture
from lambda_m034a_helpers import m034_cli_args, write_m034a_artifacts

from decodilo.lambda_cloud.m034_gate_check import (
    build_lambda_m034_gate_check_from_paths,
)


def test_m034_gate_check_passes_valid_fixture_artifacts(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(tmp_path, m029_authorization=fx["authorization"])

    report = build_lambda_m034_gate_check_from_paths(
        m028_report=fx["m028_report"],
        m029_authorization=fx["m029_authorization"],
        endpoint_confirmation=paths["endpoint_confirmation"],
        response_capture_lock=paths["response_capture_lock"],
        timeout_policy=paths["timeout_policy"],
        risk_review=paths["risk_review"],
        correlation_plan=paths["correlation_plan"],
        reconciliation_plan=paths["reconciliation_plan"],
        m034_authorization=paths["m034_authorization"],
        third_go_no_go=paths["third_go_no_go"],
        m033_report=paths["m033_report"],
    )

    assert report.gate_passed is True
    assert report.effective_launch_timeout_seconds == 30.0
    assert report.response_capture_active is True
    assert report.no_auto_launch_retry is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m034_gate_check_cli_writes_stable_non_launchable_report(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(tmp_path, m029_authorization=fx["authorization"])
    out = tmp_path / "gate.json"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m034",
        "gate-check",
        "--m028-report",
        str(fx["m028_report"]),
        "--m029-authorization",
        str(fx["m029_authorization"]),
        *m034_cli_args(paths),
        "--out",
        str(out),
    ]

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["gate_passed"] is True
    assert payload["effective_launch_timeout_seconds"] == 30.0
    assert payload["launch_ready"] is False
    assert payload["launch_allowed"] is False
