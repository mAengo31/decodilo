from lambda_m024_helpers import write_m024_prepare_inputs
from pydantic import ValidationError

from decodilo.lambda_cloud.mutation_budget_lock import load_lambda_mutation_budget_lock
from decodilo.lambda_cloud.mutation_idempotency_plan import (
    load_lambda_mutation_idempotency_plan,
)
from decodilo.lambda_cloud.mutation_resource_scope import load_lambda_mutation_resource_scope
from decodilo.lambda_cloud.real_mutation_execution_guard import (
    LambdaRealMutationExecutionGuard,
    LambdaRealMutationExecutionGuardReport,
)


def test_execution_guard_review_only_pass_possible_but_execution_impossible(tmp_path) -> None:
    refs = write_m024_prepare_inputs(tmp_path)

    report = LambdaRealMutationExecutionGuard().evaluate(
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

    assert report.review_only_passed is True
    assert report.execution_guard_passed_for_execution is False
    assert "current_milestone_forbids_execution" in report.blockers
    assert report.launch_allowed is False


def test_execution_guard_report_cannot_be_overridden_for_execution() -> None:
    try:
        LambdaRealMutationExecutionGuardReport(
            criteria=[],
            review_only_passed=True,
            execution_guard_passed_for_execution=True,
        )
    except ValidationError as exc:
        assert "cannot pass for execution" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("execution guard passed for execution")
