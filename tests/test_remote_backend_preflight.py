import json

from decodilo.cloud.dry_run import write_report
from decodilo.cloud.lambda_plan import LambdaDryRunPlanner
from decodilo.cloud.launch_preflight import run_cloud_preflight
from decodilo.cloud.launch_review import (
    build_launch_review_checklist,
    write_launch_review_checklist,
)
from decodilo.pricing.registry import import_json_snapshot
from decodilo.storage.remote_backend_requirements import (
    RemoteBackendRequirementSet,
    write_remote_backend_requirements,
)


def _cloud_artifacts(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    report = LambdaDryRunPlanner().build_plan(
        run_id="remote-preflight",
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


def test_cloud_preflight_warns_when_remote_requirements_missing(tmp_path) -> None:
    plan_path, review_path = _cloud_artifacts(tmp_path)

    result = run_cloud_preflight(
        dry_run_plan=plan_path,
        workdir=tmp_path,
        launch_review_path=review_path,
    )

    assert result.launch_ready is False
    assert result.launch_allowed is False
    assert any("remote backend requirements missing" in warning for warning in result.warnings)
    assert any("remote artifact backend not implemented" in warning for warning in result.warnings)


def test_cloud_preflight_includes_remote_requirements_when_present(tmp_path) -> None:
    plan_path, review_path = _cloud_artifacts(tmp_path)
    requirements = RemoteBackendRequirementSet(
        scenario_id="preflight",
        target_learner_count=8,
        stress_learner_count=16,
        peak_artifact_read_gbps=1,
        peak_artifact_write_gbps=1,
        peak_artifact_ops_per_second=1,
        peak_syncer_merge_gbps=1,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )
    write_remote_backend_requirements(tmp_path / "remote_backend_requirements.json", requirements)

    result = run_cloud_preflight(
        dry_run_plan=plan_path,
        workdir=tmp_path,
        launch_review_path=review_path,
    )

    evidence = result.resource_limit_summary["remote_backend_evidence"]
    assert evidence["target_learner_count"] == 8
    assert evidence["remote_backend_enabled"] is False
    assert json.loads(plan_path.read_text(encoding="utf-8"))["plan"]["launch_allowed"] is False

