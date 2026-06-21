import json
import subprocess
import sys

import pytest
from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import (
    FakeLifecycleConfig,
    execute_fake_lambda_launch,
)
from decodilo.lambda_cloud.fake_lifecycle_failures import FakeLambdaFailureConfig
from decodilo.lambda_cloud.fake_teardown_executor import execute_fake_lambda_teardown


def test_fake_lifecycle_report_schema_validates_success(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )
    lifecycle_path = tmp_path / "life" / "report.json"
    lifecycle_path.write_text(lifecycle.to_json(), encoding="utf-8")
    teardown = execute_fake_lambda_teardown(lifecycle_report_path=lifecycle_path)
    payload = json.loads(teardown.to_json())

    assert payload["fake_only"] is True
    assert payload["fake_resources_created"] == payload["fake_resources_terminated"] == 1
    assert payload["future_real_launch_candidate"] is False
    assert payload["launch_allowed"] is False


def test_fake_lifecycle_report_schema_validates_failure(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
        config=FakeLifecycleConfig(
            failure=FakeLambdaFailureConfig(failure_mode="fail_after_launch_before_health")
        ),
    )

    assert lifecycle.manual_review_required is True
    assert lifecycle.fake_lifecycle_passed is False
    assert json.loads(lifecycle.to_json())["billable_action_performed"] is False


@pytest.mark.integration
def test_fake_lifecycle_cli_preflight_run_teardown_verify_and_fault(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    preflight = tmp_path / "preflight.json"
    report_path = tmp_path / "life" / "report.json"
    teardown_path = tmp_path / "life" / "teardown.json"
    verify_path = tmp_path / "life" / "verify.json"
    fault_path = tmp_path / "fault" / "report.json"

    commands = [
        [
            "lambda",
            "fake-lifecycle",
            "preflight",
            "--m020-report",
            str(m020_path),
            "--approval-manifest",
            str(approval_path),
            "--out",
            str(preflight),
        ],
        [
            "lambda",
            "fake-lifecycle",
            "run",
            "--m020-report",
            str(m020_path),
            "--approval-manifest",
            str(approval_path),
            "--workdir",
            str(tmp_path / "life"),
            "--idempotency-key",
            "fake-launch-001",
            "--out",
            str(report_path),
        ],
        [
            "lambda",
            "fake-lifecycle",
            "teardown",
            "--lifecycle-report",
            str(report_path),
            "--out",
            str(teardown_path),
        ],
        [
            "lambda",
            "fake-lifecycle",
            "verify",
            "--lifecycle-report",
            str(report_path),
            "--teardown-report",
            str(teardown_path),
            "--out",
            str(verify_path),
        ],
        [
            "lambda",
            "fake-lifecycle",
            "fault",
            "--m020-report",
            str(m020_path),
            "--approval-manifest",
            str(approval_path),
            "--failure-mode",
            "fail_after_launch_before_health",
            "--workdir",
            str(tmp_path / "fault"),
            "--out",
            str(fault_path),
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

    assert json.loads(verify_path.read_text(encoding="utf-8"))["passed"] is True
    assert json.loads(fault_path.read_text(encoding="utf-8"))["fake_only"] is True
