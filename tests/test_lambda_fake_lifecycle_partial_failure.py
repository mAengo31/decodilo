from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import (
    FakeLifecycleConfig,
    execute_fake_lambda_launch,
)
from decodilo.lambda_cloud.fake_lifecycle_failures import FakeLambdaFailureConfig


def test_fail_after_launch_before_health_creates_recoverable_state(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)

    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
        config=FakeLifecycleConfig(
            failure=FakeLambdaFailureConfig(
                failure_mode="fail_after_launch_before_health",
            )
        ),
    )

    assert lifecycle.fake_lifecycle_passed is False
    assert lifecycle.manual_review_required is True
    assert lifecycle.failure_injection_summary["failure_mode"] == "fail_after_launch_before_health"
    assert next(iter(lifecycle.lifecycle_state.resources.values())).state == "running"


def test_process_crash_replays_fake_state_from_journal(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    first = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
        config=FakeLifecycleConfig(
            failure=FakeLambdaFailureConfig(failure_mode="process_crash_after_fake_launch")
        ),
    )
    recovered = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )

    assert first.lifecycle_journal_ref == recovered.lifecycle_journal_ref
    assert recovered.fake_resources_created == 1
    assert recovered.manual_review_required is True
