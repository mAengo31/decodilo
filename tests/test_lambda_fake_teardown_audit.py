from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch
from decodilo.lambda_cloud.fake_lifecycle_failures import FakeLambdaFailureConfig
from decodilo.lambda_cloud.fake_teardown_audit import audit_fake_lambda_teardown
from decodilo.lambda_cloud.fake_teardown_executor import execute_fake_lambda_teardown


def _launch_path(tmp_path):
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    launch = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )
    path = tmp_path / "life" / "launch.json"
    path.write_text(launch.to_json(), encoding="utf-8")
    return path


def test_clean_teardown_audit_passes(tmp_path) -> None:
    launch_path = _launch_path(tmp_path)
    teardown = execute_fake_lambda_teardown(lifecycle_report_path=launch_path)
    teardown_path = tmp_path / "life" / "teardown.json"
    teardown_path.write_text(teardown.to_json(), encoding="utf-8")

    audit = audit_fake_lambda_teardown(
        lifecycle_report=launch_path,
        teardown_report=teardown_path,
    )

    assert audit.passed is True
    assert audit.no_real_termination_commands_generated is True


def test_leftover_fake_resource_fails_teardown_audit(tmp_path) -> None:
    launch_path = _launch_path(tmp_path)
    teardown = execute_fake_lambda_teardown(
        lifecycle_report_path=launch_path,
        failure=FakeLambdaFailureConfig(failure_mode="partial_terminate_failure"),
    )
    teardown_path = tmp_path / "life" / "teardown.json"
    teardown_path.write_text(teardown.to_json(), encoding="utf-8")

    audit = audit_fake_lambda_teardown(
        lifecycle_report=launch_path,
        teardown_report=teardown_path,
    )

    assert audit.passed is False
    assert audit.manual_review_required is True
    assert audit.failed_terminate_resources


def test_teardown_audit_detects_counter_mismatch(tmp_path) -> None:
    launch_path = _launch_path(tmp_path)
    teardown = execute_fake_lambda_teardown(lifecycle_report_path=launch_path).model_copy(
        update={"fake_resources_terminated": 0}
    )
    teardown_path = tmp_path / "life" / "teardown.json"
    teardown_path.write_text(teardown.to_json(), encoding="utf-8")

    audit = audit_fake_lambda_teardown(
        lifecycle_report=launch_path,
        teardown_report=teardown_path,
    )

    assert audit.passed is False
    assert any("counters disagree" in error for error in audit.errors)
