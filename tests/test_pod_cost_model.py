from decodilo.scaling.pod_cost_model import estimate_pod_cost


def test_cost_per_token_uses_useful_tokens() -> None:
    estimate = estimate_pod_cost(
        learner_count=2,
        total_gpus=8,
        price_per_gpu_hour=2,
        raw_tokens_per_second=100,
        useful_tokens_per_second=50,
        adjusted_tokens_per_second=25,
        target_useful_tokens=1000,
    )

    assert estimate.raw_cost_per_hour == 16
    assert estimate.cost_per_useful_token > estimate.cost_per_total_token
    assert estimate.estimated_cost_to_target_tokens is not None

