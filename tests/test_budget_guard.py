from decodilo.pricing.budget import (
    BudgetGuard,
    effective_cost_per_useful_token,
    estimated_cost_for_run,
    hourly_cost_for_cluster,
    max_hours_for_budget,
)
from decodilo.pricing.models import PriceProfile


def _price() -> PriceProfile:
    return PriceProfile(
        provider="lambda",
        instance_type="gpu_8x_h100_sxm",
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        gpu_memory_gb=80,
        price_per_gpu_hour=2.5,
        price_per_instance_hour=20.0,
        region="sample",
        source_url="fixture",
        source_timestamp="2026-06-16T00:00:00Z",
    )


def test_budget_guard_rejects_over_budget_run() -> None:
    guard = BudgetGuard(starting_credits=100.0)
    decision = guard.check_run(estimated_run_cost=120.0, max_run_budget=100.0)

    assert not decision.allowed
    assert decision.reason == "planned run exceeds max_run_budget"


def test_budget_guard_accepts_under_budget_run() -> None:
    guard = BudgetGuard(starting_credits=200.0, safety_buffer_pct=0.15)
    decision = guard.check_run(estimated_run_cost=100.0, max_run_budget=150.0)

    assert decision.allowed
    assert decision.projected_remaining_credits == 85.0


def test_burn_rate_and_effective_cost_per_token() -> None:
    price = _price()

    assert hourly_cost_for_cluster(2, price) == 40.0
    assert max_hours_for_budget(100.0, 20.0) == 5.0
    assert estimated_cost_for_run(16.0, price.price_per_gpu_hour) == 40.0
    assert effective_cost_per_useful_token(50.0, 1_000) == 0.05

