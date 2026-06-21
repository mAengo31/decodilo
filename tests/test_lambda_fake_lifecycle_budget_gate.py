from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch


def test_fake_lifecycle_budget_gate_blocks_unsafe_attempt(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(
        tmp_path,
        max_run_budget=5,
    )

    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )

    assert lifecycle.fake_resources_created == 0
    assert lifecycle.fake_lifecycle_passed is False
    assert "price reconciliation must pass" in lifecycle.errors
    assert lifecycle.billable_action_performed is False
