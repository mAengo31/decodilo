from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import (
    FakeLifecycleConfig,
    execute_fake_lambda_launch,
)
from decodilo.lambda_cloud.fake_lifecycle_failures import FakeLambdaFailureConfig
from decodilo.lambda_cloud.fake_orphan_detector import detect_fake_lambda_orphans


def test_fake_orphan_detector_detects_non_terminal_fake_resource(tmp_path) -> None:
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

    report = detect_fake_lambda_orphans(lifecycle)

    assert report.fake_orphan_count == 1
    assert report.manual_review_required is True
    assert report.no_mutations_performed is True


def test_fake_orphan_detector_reports_unmanaged_live_resources(tmp_path) -> None:
    base_report, _base_path, approval_path = write_approved_m020(tmp_path)
    resource_report = base_report.resource_reconciliation.model_copy(
        update={"unmanaged_billable_instances": 2}
    )
    _report, m020_path, _approval_path = write_approved_m020(
        tmp_path,
        report_updates={"resource_reconciliation": resource_report},
    )
    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )

    report = detect_fake_lambda_orphans(lifecycle)

    assert report.unmanaged_live_count == 2
    assert report.manual_review_required is True
