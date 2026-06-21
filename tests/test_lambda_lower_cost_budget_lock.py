from lambda_m038_helpers import canonical_readiness

from decodilo.lambda_cloud.lower_cost_budget_lock import (
    build_lambda_lower_cost_budget_lock,
)


def test_lower_cost_budget_lock_passes_under_budget():
    report = build_lambda_lower_cost_budget_lock(canonical_readiness())

    assert report.budget_lock_passed is True
    assert report.estimated_cost == 1.645
    assert report.buffered_estimated_cost == 1.89175
    assert report.non_sample_price is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lower_cost_budget_lock_blocks_runtime_over_30():
    report = build_lambda_lower_cost_budget_lock(
        canonical_readiness(),
        planned_runtime_minutes=31,
    )

    assert report.budget_lock_passed is False
    assert "planned_runtime_exceeds_30_minutes" in report.blockers
