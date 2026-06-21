from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import (
    FakeLifecycleConfig,
    execute_fake_lambda_launch,
)
from decodilo.lambda_cloud.fake_lifecycle_failures import FakeLambdaFailureConfig
from decodilo.lambda_cloud.fake_lifecycle_reconciler import reconcile_fake_lambda_lifecycle
from decodilo.lambda_cloud.fake_teardown_executor import execute_fake_lambda_teardown


def test_fake_lifecycle_reconcile_reports_clean_teardown(tmp_path) -> None:
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

    reconciliation = reconcile_fake_lambda_lifecycle(teardown)

    assert reconciliation.fake_created_resources == 1
    assert reconciliation.fake_terminated_resources == 1
    assert reconciliation.fake_orphan_count == 0
    assert reconciliation.no_mutations_performed is True


def test_fake_lifecycle_reconcile_reports_orphan(tmp_path) -> None:
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

    reconciliation = reconcile_fake_lambda_lifecycle(lifecycle)

    assert reconciliation.fake_orphan_count == 1
    assert reconciliation.manual_review_required is True
