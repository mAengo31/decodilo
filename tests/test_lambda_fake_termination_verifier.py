from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch
from decodilo.lambda_cloud.fake_lifecycle_failures import FakeLambdaFailureConfig
from decodilo.lambda_cloud.fake_teardown_executor import execute_fake_lambda_teardown
from decodilo.lambda_cloud.fake_termination_verifier import verify_fake_lambda_termination


def test_fake_termination_verification_passes_clean_teardown(tmp_path) -> None:
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

    verification = verify_fake_lambda_termination(teardown)

    assert verification.passed is True
    assert verification.no_real_termination_commands_generated is True
    assert verification.launch_allowed is False


def test_fake_termination_verification_fails_if_resource_remains(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )

    verification = verify_fake_lambda_termination(lifecycle)

    assert verification.passed is False
    assert verification.manual_review_required is True
    assert "fake resources remain" in verification.errors[0]


def test_fake_termination_verification_detects_failed_terminate(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )
    lifecycle_path = tmp_path / "life" / "report.json"
    lifecycle_path.write_text(lifecycle.to_json(), encoding="utf-8")
    teardown = execute_fake_lambda_teardown(
        lifecycle_report_path=lifecycle_path,
        failure=FakeLambdaFailureConfig(failure_mode="terminate_timeout"),
    )

    verification = verify_fake_lambda_termination(teardown)

    assert verification.passed is False
    assert verification.fake_orphan_candidates == 1
