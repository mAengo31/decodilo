import json
import subprocess
import sys
from pathlib import Path

from lambda_m050_helpers import write_m050_inputs

from decodilo.lambda_cloud.m050_report import build_lambda_m050_report_from_paths


def test_m050_report_summarizes_future_metadata_bootstrap(tmp_path):
    paths = write_m050_inputs(tmp_path)

    report = build_lambda_m050_report_from_paths(
        scope=paths["scope"],
        access_policy=paths["access"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )

    assert report.report_passed is True
    assert report.selected_bootstrap_mode == "lifecycle_plus_metadata_only"
    assert report.ssh_approval_status == "declined_no_ssh"
    assert (
        report.m051_authorization_status
        == "authorized_for_future_m051_metadata_only_bootstrap_review"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False


def test_m050_report_cli_writes_future_only_report(tmp_path):
    paths = write_m050_inputs(tmp_path / "artifacts")
    out = tmp_path / "m050-cli.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "m050",
            "report",
            "--scope",
            str(paths["scope"]),
            "--access-policy",
            str(paths["access"]),
            "--risk-review",
            str(paths["risk"]),
            "--authorization",
            str(paths["authorization"]),
            "--runbook-preview",
            str(paths["runbook"]),
            "--out",
            str(out),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["report_passed"] is True
    assert payload["launch_ready"] is False
    assert payload["launch_allowed"] is False
