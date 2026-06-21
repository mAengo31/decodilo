from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch


def test_fake_launch_succeeds_with_complete_fake_approval(tmp_path) -> None:
    report, m020_path, approval_path = write_approved_m020(tmp_path)

    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )

    assert report.approval_gate_report.approval_passed is True
    assert lifecycle.fake_lifecycle_passed is True
    assert lifecycle.fake_resources_created == 1
    assert lifecycle.fake_resources_terminated == 0
    assert lifecycle.real_lambda_api_used is False
    assert lifecycle.billable_action_performed is False
    assert lifecycle.launch_ready is False
    assert lifecycle.launch_allowed is False


def test_fake_launch_blocks_without_approval(tmp_path) -> None:
    _report, m020_path, _approval_path = write_approved_m020(
        tmp_path,
        with_approval=False,
    )
    bad_approval = tmp_path / "missing-approval.json"

    try:
        execute_fake_lambda_launch(
            m020_report_path=m020_path,
            approval_manifest_path=bad_approval,
            workdir=tmp_path / "life",
            idempotency_key="fake-launch-001",
        )
    except FileNotFoundError:
        blocked = True
    else:
        blocked = False

    assert blocked is True


def test_fake_launch_blocks_over_budget(tmp_path) -> None:
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

    assert lifecycle.fake_lifecycle_passed is False
    assert any("price reconciliation must pass" in error for error in lifecycle.errors)


def test_fake_launch_blocks_unmanaged_billable_resources(tmp_path) -> None:
    report, _m020_path, approval_path = write_approved_m020(tmp_path)
    resource_report = report.resource_reconciliation.model_copy(
        update={
            "unmanaged_billable_instances": 1,
            "manual_review_required": True,
            "resource_reconciliation_passed": False,
        }
    )
    report, m020_path, _approval_path = write_approved_m020(
        tmp_path,
        report_updates={"resource_reconciliation": resource_report},
    )

    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )

    assert report.resource_reconciliation.unmanaged_billable_instances == 1
    assert lifecycle.fake_lifecycle_passed is False
    assert any("resource reconciliation must pass" in error for error in lifecycle.errors)


def test_fake_launch_does_not_call_real_lambda(monkeypatch, tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)

    def explode(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("real client should not be constructed")

    monkeypatch.setattr(
        "decodilo.lambda_cloud.live_read_only_client.LiveReadOnlyLambdaCloudClient",
        explode,
        raising=False,
    )
    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )

    assert lifecycle.real_lambda_api_used is False
