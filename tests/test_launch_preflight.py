import json
import subprocess
import sys

from decodilo.cloud.dry_run import write_report
from decodilo.cloud.lambda_plan import LambdaDryRunPlanner
from decodilo.cloud.launch_preflight import run_cloud_preflight
from decodilo.cloud.launch_review import (
    build_launch_review_checklist,
    write_launch_review_checklist,
)
from decodilo.pricing.registry import import_json_snapshot


def _cloud_artifacts(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    report = LambdaDryRunPlanner().build_plan(
        run_id="preflight-cloud",
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


def test_cloud_preflight_passes_safety_but_launch_stays_false(tmp_path) -> None:
    plan_path, review_path = _cloud_artifacts(tmp_path)

    result = run_cloud_preflight(dry_run_plan=plan_path, launch_review_path=review_path)

    assert result.passed is True
    assert result.preflight_passed is True
    assert result.safety_checks_passed is True
    assert result.artifact_checks_passed is True
    assert result.budget_checks_passed is True
    assert result.launch_review_passed is False
    assert result.launch_ready is False
    assert result.launch_allowed is False
    assert result.budget_summary is not None
    assert result.scaling_summary is not None
    assert "cloud launch is disabled in this build" in result.warnings


def test_cloud_preflight_fails_missing_review(tmp_path) -> None:
    plan_path, review_path = _cloud_artifacts(tmp_path)
    review_path.unlink()

    result = run_cloud_preflight(dry_run_plan=plan_path, launch_review_path=review_path)

    assert result.passed is False
    assert any("launch review" in error for error in result.errors)


def test_cloud_preflight_cli_writes_report(tmp_path) -> None:
    plan_path, review_path = _cloud_artifacts(tmp_path)
    out = tmp_path / "preflight.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "preflight",
            "cloud",
            "--dry-run-plan",
            str(plan_path),
            "--launch-review",
            str(review_path),
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert json.loads(completed.stdout)["launch_allowed"] is False
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["preflight_passed"] is True
    assert written["launch_ready"] is False
    assert written["launch_allowed"] is False
