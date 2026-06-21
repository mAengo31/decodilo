from decodilo.scaling.scavenged_compute import ScavengedPodSupply, estimate_scavenged_compute


def test_scavenged_discount_lowers_cost_when_useful() -> None:
    supply = ScavengedPodSupply(
        expected_extra_learners=2,
        availability_window_seconds=3600,
        preemption_rate_per_hour=0.01,
        startup_time_seconds=10,
        discount_vs_base=0.7,
        max_extra_learners=4,
        join_leave_frequency=0.1,
    )

    estimate = estimate_scavenged_compute(
        supply=supply,
        per_learner_token_rate=100,
        base_price_per_learner_hour=2,
        artifact_bytes_per_learner_sync=1024,
        checkpoint_bytes_per_learner=2048,
    )

    assert estimate.expected_extra_useful_tokens > 0
    assert estimate.expected_cost_savings > 0
    assert estimate.expected_artifact_pressure_increase > 0


def test_high_preemption_reduces_scavenged_value() -> None:
    low = ScavengedPodSupply(
        expected_extra_learners=1,
        availability_window_seconds=3600,
        preemption_rate_per_hour=0,
        startup_time_seconds=0,
        discount_vs_base=0.5,
        max_extra_learners=1,
        join_leave_frequency=0,
    )
    high = low.model_copy(update={"preemption_rate_per_hour": 10})

    low_estimate = estimate_scavenged_compute(
        supply=low,
        per_learner_token_rate=100,
        base_price_per_learner_hour=2,
        artifact_bytes_per_learner_sync=1024,
        checkpoint_bytes_per_learner=2048,
    )
    high_estimate = estimate_scavenged_compute(
        supply=high,
        per_learner_token_rate=100,
        base_price_per_learner_hour=2,
        artifact_bytes_per_learner_sync=1024,
        checkpoint_bytes_per_learner=2048,
    )

    assert high_estimate.expected_extra_useful_tokens < low_estimate.expected_extra_useful_tokens

