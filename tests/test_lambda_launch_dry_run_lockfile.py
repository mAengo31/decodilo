from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from decodilo.lambda_cloud.launch_dry_run_lockfile import (
    LambdaLaunchDryRunLockfile,
    build_lambda_launch_dry_run_lockfile,
)


def test_dry_run_lockfile_builds_non_executable():
    lock = build_lambda_launch_dry_run_lockfile(
        run_id="run",
        launch_plan_hash="a",
        teardown_plan_hash="b",
        budget_lock_hash="c",
        approval_hash="d",
        operation_spec_hash="e",
        termination_runbook_hash="f",
        launch_window_policy_hash="g",
    )

    assert lock.locked_for_review_only is True
    assert lock.executable is False
    assert lock.launch_allowed is False


def test_dry_run_lockfile_rejects_executable_true():
    try:
        LambdaLaunchDryRunLockfile(
            run_id="run",
            launch_plan_hash="a",
            teardown_plan_hash="b",
            budget_lock_hash="c",
            approval_hash="d",
            operation_spec_hash="e",
            termination_runbook_hash="f",
            launch_window_policy_hash="g",
            executable=True,
        )
    except ValidationError:
        return
    raise AssertionError("expected executable lockfile to be rejected")


def test_dry_run_lockfile_rejects_expired_lock():
    expired = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()

    try:
        build_lambda_launch_dry_run_lockfile(
            run_id="run",
            launch_plan_hash="a",
            teardown_plan_hash="b",
            budget_lock_hash="c",
            approval_hash="d",
            operation_spec_hash="e",
            termination_runbook_hash="f",
            launch_window_policy_hash="g",
            expires_at_utc=expired,
        )
    except ValidationError:
        return
    raise AssertionError("expected expired lockfile to be rejected")
