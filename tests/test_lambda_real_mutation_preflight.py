from lambda_m024_helpers import write_m024_prepare_inputs

from decodilo.lambda_cloud.mutation_budget_lock import load_lambda_mutation_budget_lock
from decodilo.lambda_cloud.mutation_idempotency_plan import (
    load_lambda_mutation_idempotency_plan,
)
from decodilo.lambda_cloud.mutation_resource_scope import load_lambda_mutation_resource_scope
from decodilo.lambda_cloud.preflight import run_lambda_preflight
from decodilo.lambda_cloud.real_mutation_execution_guard import (
    LambdaRealMutationExecutionGuard,
)
from decodilo.lambda_cloud.real_mutation_preflight import (
    run_lambda_real_mutation_preflight,
)
from decodilo.lambda_cloud.real_mutation_skeleton_audit import (
    LambdaRealMutationSkeletonAuditReport,
    audit_lambda_real_mutation_skeleton,
)


def _guard_report(refs):
    return LambdaRealMutationExecutionGuard().evaluate(
        operation_name="launch_one_instance",
        operation_allowed_by_spec=True,
        approval_present=True,
        budget_lock=load_lambda_mutation_budget_lock(refs["budget"]),
        resource_scope=load_lambda_mutation_resource_scope(refs["scope"]),
        teardown_plan_present=True,
        termination_policy_present=True,
        idempotency_plan=load_lambda_mutation_idempotency_plan(refs["idempotency"]),
        kill_switch_present=True,
        live_read_only_discovery_present=True,
        no_unmanaged_billable_resources=True,
        launch_window_policy_present=True,
    )


def test_real_mutation_preflight_includes_skeleton_status(tmp_path) -> None:
    refs = write_m024_prepare_inputs(tmp_path)
    audit = audit_lambda_real_mutation_skeleton(".")
    report = run_lambda_real_mutation_preflight(
        skeleton_audit=audit,
        execution_guard=_guard_report(refs),
        budget_lock=refs["budget"],
        idempotency_plan=refs["idempotency"],
        resource_scope=refs["scope"],
    )

    assert report.preflight_status == "blocked_for_execution"
    assert report.skeleton_audit_summary["passed"] is True
    assert report.real_mutation_enabled is False
    assert report.launch_allowed is False


def test_lambda_preflight_includes_m024_skeleton_summary() -> None:
    report = run_lambda_preflight(
        real_mutation_skeleton_audit=audit_lambda_real_mutation_skeleton(".")
    )

    assert report.real_mutation_skeleton_summary is not None
    assert report.real_mutation_skeleton_summary["passed"] is True
    assert report.launch_allowed is False
    assert any("mutation skeleton present but disabled" in warning for warning in report.warnings)


def test_skeleton_failure_creates_preflight_blocker() -> None:
    audit = LambdaRealMutationSkeletonAuditReport(
        passed=False,
        real_mutation_code_detected=True,
        errors=["synthetic failure"],
    )
    report = run_lambda_real_mutation_preflight(skeleton_audit=audit)

    assert "skeleton audit failed" in report.blockers
    assert report.launch_allowed is False
