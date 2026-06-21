import json
import subprocess
import sys

import pytest
from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch
from decodilo.lambda_cloud.fake_lifecycle_preflight import (
    run_fake_lambda_lifecycle_preflight,
    write_fake_lambda_lifecycle_preflight_report,
)
from decodilo.lambda_cloud.fake_teardown_audit import (
    audit_fake_lambda_teardown,
    write_fake_lambda_teardown_audit_report,
)
from decodilo.lambda_cloud.fake_teardown_executor import execute_fake_lambda_teardown

pytestmark = pytest.mark.integration


def test_m022_fake_lifecycle_cli_commands(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    stress_path = tmp_path / "stress.json"
    absence_path = tmp_path / "absence.json"
    contract_path = tmp_path / "contract.json"
    package_path = tmp_path / "package.json"
    preflight_path = tmp_path / "preflight.json"
    teardown_audit_path = tmp_path / "teardown-audit.json"
    preflight = run_fake_lambda_lifecycle_preflight(
        m020_report=m020_path,
        approval_manifest=approval_path,
    )
    write_fake_lambda_lifecycle_preflight_report(preflight_path, preflight)
    launch = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )
    launch_path = tmp_path / "life" / "launch.json"
    launch_path.write_text(launch.to_json(), encoding="utf-8")
    teardown = execute_fake_lambda_teardown(lifecycle_report_path=launch_path)
    teardown_path = tmp_path / "life" / "teardown.json"
    teardown_path.write_text(teardown.to_json(), encoding="utf-8")
    teardown_audit = audit_fake_lambda_teardown(
        lifecycle_report=launch_path,
        teardown_report=teardown_path,
    )
    write_fake_lambda_teardown_audit_report(teardown_audit_path, teardown_audit)

    commands = [
        [
            "lambda",
            "fake-mutation",
            "contract",
            "--lifecycle-report",
            str(teardown_path),
            "--out",
            str(contract_path),
        ],
        [
            "lambda",
            "fake-lifecycle",
            "stress",
            "--m020-report",
            str(m020_path),
            "--approval-manifest",
            str(approval_path),
            "--workdir",
            str(tmp_path / "stress"),
            "--cycles",
            "1",
            "--failure-modes",
            "none",
            "--out",
            str(stress_path),
        ],
        [
            "lambda",
            "fake-lifecycle",
            "teardown-audit",
            "--lifecycle-report",
            str(launch_path),
            "--teardown-report",
            str(teardown_path),
            "--out",
            str(teardown_audit_path),
        ],
        [
            "lambda",
            "real-mutation-absence-audit",
            "--project-root",
            ".",
            "--out",
            str(absence_path),
        ],
        [
            "lambda",
            "fake-lifecycle",
            "evidence-package",
            "--m020-report",
            str(m020_path),
            "--approval-manifest",
            str(approval_path),
            "--preflight-report",
            str(preflight_path),
            "--stress-report",
            str(stress_path),
            "--teardown-audit",
            str(teardown_audit_path),
            "--out",
            str(package_path),
        ],
    ]
    for command in commands:
        completed = subprocess.run(
            [sys.executable, "-m", "decodilo.cli", *command],
            check=True,
            capture_output=True,
            text=True,
        )
        assert json.loads(completed.stdout)["launch_allowed"] is False

    assert json.loads(package_path.read_text(encoding="utf-8"))["blockers"] == []


def test_m022_fake_mutation_contract_cli_fails_missing_report(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "fake-mutation",
            "contract",
            "--lifecycle-report",
            str(tmp_path / "missing.json"),
            "--out",
            str(tmp_path / "contract.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
