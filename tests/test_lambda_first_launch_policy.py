from decodilo.lambda_cloud.first_launch_policy import evaluate_first_launch_policy
from decodilo.lambda_cloud.launch_plan import build_lambda_launch_plan
from decodilo.lambda_cloud.live_resource_ledger import LambdaLiveResourceLedgerReport
from decodilo.lambda_cloud.teardown_plan import build_lambda_teardown_plan


def _plan(*, nodes: int = 1, hours: float = 0.5, budget: float = 50):
    return build_lambda_launch_plan(
        run_id="run",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=nodes,
        gpus_per_instance=8,
        hours=hours,
        max_run_budget=budget,
    )


def test_lambda_first_launch_policy_rejects_default_limit_violations() -> None:
    report = evaluate_first_launch_policy(
        launch_plan=_plan(nodes=2, hours=1, budget=100),
        teardown_plan=build_lambda_teardown_plan(run_id="run", planned_node_ids=[]),
        budget_manifest_present=True,
        approval_present=True,
        live_discovery_present=True,
        read_only_audit_present=True,
    )

    assert "too_many_instances" in report.violations
    assert "runtime_too_long" in report.violations
    assert "budget_limit_too_high" in report.violations
    assert report.launch_allowed is False


def test_lambda_first_launch_policy_rejects_missing_teardown_and_unmanaged_billable() -> None:
    report = evaluate_first_launch_policy(
        launch_plan=_plan(),
        ledger_report=LambdaLiveResourceLedgerReport(
            run_id="run",
            discovered_count=1,
            planned_count=1,
            matched_count=0,
            unmanaged_count=1,
            billable_state_count=1,
            live_api_used=True,
        ),
        budget_manifest_present=True,
        approval_present=True,
        live_discovery_present=True,
        read_only_audit_present=True,
    )

    assert "missing_teardown_plan" in report.violations
    assert "unmanaged_billable_resources" in report.violations
