from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch


def test_duplicate_fake_launch_returns_existing_resources(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    first = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )
    second = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )

    assert first.fake_resources_created == 1
    assert second.fake_resources_created == 1
    assert list(first.lifecycle_state.resources) == list(second.lifecycle_state.resources)
    assert "duplicate fake launch" in second.warnings[0]
