import json
import subprocess
import sys

from lambda_m029_helpers import m029_fixture
from lambda_m034a_helpers import m034_cli_args, write_m034a_artifacts

CONFIRM_BILLABLE = (
    "I understand this may create a billable Lambda instance and must be terminated"
)
CONFIRM_TERMINATE = (
    "I understand this run must terminate the owned instance and verify termination"
)


def _base_run_cmd(fx, workdir):
    return [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--m028-report",
        str(fx["m028_report"]),
        "--m029-authorization",
        str(fx["m029_authorization"]),
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        CONFIRM_BILLABLE,
        "--confirm-terminate-required",
        CONFIRM_TERMINATE,
    ]


def test_m034_run_blocks_partial_artifact_set_before_request(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(tmp_path, m029_authorization=fx["authorization"])
    workdir = tmp_path / "partial"
    cmd = [
        *_base_run_cmd(fx, workdir),
        "--endpoint-confirmation",
        str(paths["endpoint_confirmation"]),
    ]

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)

    assert completed.returncode != 0
    assert "requires all M033/M034 artifacts" in completed.stderr
    assert not (workdir / "report.json").exists()


def test_m034_run_accepts_full_artifact_set_and_records_gate_metadata(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(tmp_path, m029_authorization=fx["authorization"])
    workdir = tmp_path / "valid"
    cmd = [*_base_run_cmd(fx, workdir), *m034_cli_args(paths)]

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr
    payload = json.loads((workdir / "report.json").read_text(encoding="utf-8"))
    assert payload["launch_timeout_seconds_effective"] == 30.0
    assert payload["response_capture_active"] is True
    assert payload["status_before_parse"] is True
    assert payload["body_sample_enabled"] is False
    assert payload["no_auto_launch_retry"] is True
    assert payload["real_lambda_api_used"] is False
    assert payload["billable_action_performed"] is False
    assert payload["launch_ready"] is False
    assert payload["launch_allowed"] is False
