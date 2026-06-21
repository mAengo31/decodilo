import pytest

from decodilo.scaling.learner_pods import LearnerPodScalingScenario
from decodilo.scaling.learner_scaling_model import evaluate_learner_scaling
from decodilo.storage.remote_backend_requirements import (
    RemoteBackendRequirementSet,
    requirements_from_scaling_report,
)


def _scaling_report():
    scenario = LearnerPodScalingScenario(
        scenario_id="remote-req",
        mode="fixed_total_compute",
        candidate_learner_counts=[1, 2],
        fixed_total_gpus=4,
        training_duration_hours=1,
        model_parameter_count=1000,
        bytes_per_parameter=2,
        fragment_count=4,
        chunk_size_bytes=1024,
        sync_interval_steps=100,
        local_step_seconds=1,
        calibration_profile={
            "per_gpu_token_rate": 1000,
            "failure_rate_per_hour": 0.01,
            "recovery_time_seconds": 300,
        },
    )
    return evaluate_learner_scaling(scenario)


def test_requirement_set_builds_from_scaling_report_and_round_trips() -> None:
    requirements = requirements_from_scaling_report(_scaling_report())

    assert requirements.target_learner_count > 0
    assert requirements.stress_learner_count >= requirements.target_learner_count
    assert RemoteBackendRequirementSet.model_validate_json(
        requirements.stable_json()
    ) == requirements


def test_requirement_set_rejects_negative_throughput() -> None:
    with pytest.raises(ValueError):
        RemoteBackendRequirementSet(
            scenario_id="bad",
            target_learner_count=8,
            stress_learner_count=16,
            peak_artifact_read_gbps=-1,
            peak_artifact_write_gbps=1,
            peak_artifact_ops_per_second=1,
            peak_syncer_merge_gbps=1,
            checkpoint_storage_growth_gb_per_hour=1,
            event_log_growth_mb_per_hour=1,
            required_replay_snapshot_frequency="every checkpoint",
        )


def test_requirement_set_rejects_missing_critical_requirement() -> None:
    with pytest.raises(ValueError):
        RemoteBackendRequirementSet(
            scenario_id="bad",
            target_learner_count=8,
            stress_learner_count=4,
            peak_artifact_read_gbps=1,
            peak_artifact_write_gbps=1,
            peak_artifact_ops_per_second=1,
            peak_syncer_merge_gbps=1,
            checkpoint_storage_growth_gb_per_hour=1,
            event_log_growth_mb_per_hour=1,
            required_replay_snapshot_frequency="every checkpoint",
        )

