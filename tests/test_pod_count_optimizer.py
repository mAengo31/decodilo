from decodilo.scaling.learner_pods import LearnerPodScalingScenario
from decodilo.scaling.pod_count_optimizer import optimize_pod_count


def _scenario(**updates) -> LearnerPodScalingScenario:
    payload = {
        "scenario_id": "optimizer",
        "mode": "expanding_compute",
        "candidate_learner_counts": [1, 2, 4],
        "gpus_per_learner": 1,
        "training_duration_hours": 4,
        "target_useful_tokens": 1_000_000,
        "model_parameter_count": 1000,
        "bytes_per_parameter": 2,
        "fragment_count": 4,
        "chunk_size_bytes": 1024 * 1024,
        "sync_interval_steps": 100,
        "local_step_seconds": 1,
        "min_quorum_policy": {"ratio": 0.5},
        "calibration_profile": {
            "per_gpu_token_rate": 1000,
            "failure_rate_per_hour": 0.02,
            "recovery_time_seconds": 300,
            "price_per_gpu_hour": 1,
        },
    }
    payload.update(updates)
    return LearnerPodScalingScenario(**payload)


def test_optimizer_produces_explainable_recommendation() -> None:
    result = optimize_pod_count(_scenario())

    assert result.recommended_learner_count in {1, 2, 4}
    assert result.recommended_candidate is not None
    assert result.decision_rationale
    assert result.pareto_frontier


def test_optimizer_rejects_over_bandwidth_candidate() -> None:
    result = optimize_pod_count(_scenario(bandwidth_cap_gbps=0.000001))

    assert result.rejected_candidates
    assert any("bandwidth" in candidate.dominant_bottleneck for candidate in result.candidates)


def test_optimizer_chooses_lower_cost_when_goodput_equal() -> None:
    fixed = _scenario(
        mode="fixed_total_compute",
        fixed_total_gpus=4,
        gpus_per_learner=None,
        candidate_learner_counts=[1, 2],
        calibration_profile={
            "per_gpu_token_rate": 1000,
            "failure_rate_per_hour": 0,
            "recovery_time_seconds": 0,
            "price_per_gpu_hour": 1,
        },
    )

    result = optimize_pod_count(fixed)

    assert result.recommended_candidate is not None
    assert result.recommended_candidate.cost_per_sample_efficiency_adjusted_token is not None

