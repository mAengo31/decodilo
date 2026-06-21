from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch
from decodilo.lambda_cloud.fake_lifecycle_failures import FakeLambdaFailureConfig
from decodilo.lambda_cloud.fake_teardown_executor import execute_fake_lambda_teardown


def test_fake_teardown_terminates_fake_resources(tmp_path) -> None:
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

    assert teardown.fake_resources_terminated == 1
    assert teardown.fake_lifecycle_passed is True
    assert all(
        record.state == "terminated"
        for record in teardown.lifecycle_state.resources.values()
    )


def test_fake_teardown_is_idempotent(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )
    lifecycle_path = tmp_path / "life" / "report.json"
    lifecycle_path.write_text(lifecycle.to_json(), encoding="utf-8")
    first = execute_fake_lambda_teardown(lifecycle_report_path=lifecycle_path)
    lifecycle_path.write_text(first.to_json(), encoding="utf-8")
    second = execute_fake_lambda_teardown(lifecycle_report_path=lifecycle_path)

    assert first.fake_resources_terminated == second.fake_resources_terminated == 1
    assert second.fake_lifecycle_passed is True


def test_fake_teardown_failure_requires_manual_review(tmp_path) -> None:
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
        failure=FakeLambdaFailureConfig(failure_mode="partial_terminate_failure"),
    )

    assert teardown.manual_review_required is True
    assert teardown.fake_lifecycle_passed is False
    assert next(iter(teardown.lifecycle_state.resources.values())).state == "failed_terminate"
