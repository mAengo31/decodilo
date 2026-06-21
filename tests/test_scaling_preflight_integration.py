import json

from decodilo.cloud.dry_run import write_report
from decodilo.cloud.lambda_plan import LambdaDryRunPlanner
from decodilo.cloud.launch_preflight import run_cloud_preflight
from decodilo.cloud.launch_review import (
    build_launch_review_checklist,
    write_launch_review_checklist,
)
from decodilo.pricing.registry import import_json_snapshot
from decodilo.scaling.learner_pods import LearnerPodScalingScenario
from decodilo.scaling.learner_scaling_model import evaluate_learner_scaling
from decodilo.scaling.scaling_report import write_scaling_decision_report


def _cloud_artifacts(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    report = LambdaDryRunPlanner().build_plan(
        run_id="scaling-preflight",
        price_snapshot_path=snapshot_path,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        nodes=1,
        hours=1,
        credits=7500,
        max_run_budget=1000,
        params=1_000_000,
        bytes_per_param=2,
        expected_tokens_per_second=1000,
        expected_goodput=0.9,
    )
    plan_path = tmp_path / "dry-run.json"
    review_path = tmp_path / "launch-review.json"
    write_report(plan_path, report)
    write_launch_review_checklist(review_path, build_launch_review_checklist(report))
    return plan_path, review_path


def test_cloud_preflight_warns_when_scaling_report_missing(tmp_path) -> None:
    plan_path, review_path = _cloud_artifacts(tmp_path)

    result = run_cloud_preflight(dry_run_plan=plan_path, launch_review_path=review_path)

    assert result.launch_ready is False
    assert result.launch_allowed is False
    assert any("learner scaling report missing" in warning for warning in result.warnings)


def test_cloud_preflight_includes_backend_targets_when_report_present(tmp_path) -> None:
    plan_path, review_path = _cloud_artifacts(tmp_path)
    scenario = LearnerPodScalingScenario(
        scenario_id="preflight-scaling",
        mode="fixed_total_compute",
        candidate_learner_counts=[1, 2],
        fixed_total_gpus=8,
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
    write_scaling_decision_report(
        tmp_path / "learner_scaling_report.json",
        evaluate_learner_scaling(scenario),
    )

    result = run_cloud_preflight(dry_run_plan=plan_path, launch_review_path=review_path)

    assert result.resource_limit_summary["backend_design_targets"] is not None
    assert result.launch_ready is False
    assert result.launch_allowed is False


def test_scaling_report_json_remains_stable(tmp_path) -> None:
    plan_path, _ = _cloud_artifacts(tmp_path)
    assert json.loads(plan_path.read_text(encoding="utf-8"))["plan"]["launch_allowed"] is False

