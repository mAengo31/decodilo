from lambda_m028_helpers import write_m028_core_artifacts

from decodilo.lambda_cloud.final_budget_lock import (
    LambdaFinalBudgetLock,
    build_lambda_final_budget_lock,
)


def test_final_budget_lock_builds(tmp_path):
    paths = write_m028_core_artifacts(tmp_path)

    lock = build_lambda_final_budget_lock(paths["m020"])

    assert lock.budget_lock_passed is True
    assert lock.max_budget <= 50
    assert lock.launch_allowed is False


def test_over_budget_lock_blocks():
    lock = LambdaFinalBudgetLock(
        m020_report_ref="m020",
        max_budget=51,
        max_runtime_minutes=30,
        max_instances=1,
        planned_hours=0.5,
        selected_price_record_id="price",
        price_snapshot_id="snap",
        safety_buffer_adjusted_cost=10,
        lock_hash="hash",
        budget_lock_passed=False,
        blockers=["max budget exceeds 50 USD"],
    )

    assert lock.budget_lock_passed is False
    assert lock.launch_allowed is False
