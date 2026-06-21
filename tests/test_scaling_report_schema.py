import json

from decodilo.scaling.learner_pods import LearnerPodScalingScenario
from decodilo.scaling.learner_scaling_model import evaluate_learner_scaling


def test_scaling_decision_report_schema_and_cloud_state() -> None:
    scenario = LearnerPodScalingScenario(
        scenario_id="report",
        mode="fixed_total_compute",
        candidate_learner_counts=[1, 2],
        fixed_total_gpus=4,
        training_duration_hours=1,
        model_parameter_count=1000,
        bytes_per_parameter=2,
        fragment_count=4,
        chunk_size_bytes=1024 * 1024,
        sync_interval_steps=100,
        local_step_seconds=1,
        calibration_profile={
            "per_gpu_token_rate": 1000,
            "failure_rate_per_hour": 0.01,
            "recovery_time_seconds": 300,
        },
    )

    report = evaluate_learner_scaling(scenario)
    payload = json.loads(report.to_json())

    assert payload["report_schema_version"] == 1
    assert payload["backend_design_targets"]["target_learner_count"] is not None
    assert payload["cloud_state"] == {"launch_allowed": False, "launch_ready": False}
    assert payload["limitations"]

