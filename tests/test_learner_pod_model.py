import pytest

from decodilo.scaling.learner_pods import LearnerPodScalingScenario, LearnerPodShape


def test_learner_pod_shape_validates_and_round_trips_json() -> None:
    shape = LearnerPodShape(
        shape_id="shape-a",
        learner_count=4,
        gpus_per_learner=2,
        total_gpus=8,
        per_learner_token_rate=1000,
        learner_failure_rate_per_hour=0.01,
        learner_recovery_time_seconds=300,
    )

    assert LearnerPodShape.model_validate_json(shape.stable_json()) == shape


def test_learner_pod_shape_rejects_total_gpu_mismatch() -> None:
    with pytest.raises(ValueError, match="total_gpus"):
        LearnerPodShape(
            shape_id="bad",
            learner_count=4,
            gpus_per_learner=2,
            total_gpus=7,
            per_learner_token_rate=1000,
            learner_failure_rate_per_hour=0.01,
            learner_recovery_time_seconds=300,
        )


def test_scaling_scenario_supports_modes_and_validation() -> None:
    fixed = LearnerPodScalingScenario(
        scenario_id="fixed",
        mode="fixed_total_compute",
        candidate_learner_counts=[1, 2, 4],
        fixed_total_gpus=8,
        training_duration_hours=1,
        model_parameter_count=100,
        bytes_per_parameter=2,
        fragment_count=4,
        chunk_size_bytes=1024,
        sync_interval_steps=10,
        local_step_seconds=1,
    )
    assert fixed.total_gpus_for(4) == 8
    assert fixed.min_quorum_for(4) == 2

    expanding = fixed.model_copy(
        update={
            "scenario_id": "expanding",
            "mode": "expanding_compute",
            "fixed_total_gpus": None,
            "gpus_per_learner": 2,
        }
    )
    assert expanding.total_gpus_for(4) == 8

    scavenged = expanding.model_copy(
        update={"scenario_id": "scavenged", "mode": "scavenged_compute"}
    )
    assert scavenged.total_gpus_for(2) == 4


def test_scaling_scenario_rejects_impossible_config() -> None:
    with pytest.raises(ValueError):
        LearnerPodScalingScenario(
            scenario_id="bad",
            mode="fixed_total_compute",
            candidate_learner_counts=[0],
            fixed_total_gpus=8,
            training_duration_hours=1,
            fragment_count=4,
            chunk_size_bytes=1024,
            sync_interval_steps=10,
            local_step_seconds=1,
        )
