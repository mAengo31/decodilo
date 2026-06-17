import json
import subprocess
import sys

from decodilo.cloud.launch_review import build_launch_review_checklist
from decodilo.pricing.registry import import_json_snapshot


def _report(tmp_path):
    from decodilo.cloud.lambda_plan import LambdaDryRunPlanner

    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    return LambdaDryRunPlanner().build_plan(
        run_id="review",
        price_snapshot_path=snapshot_path,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        nodes=1,
        hours=1,
        credits=7500,
        max_run_budget=1000,
    )


def test_launch_review_fails_without_operator_ack_and_includes_teardown(tmp_path) -> None:
    checklist = build_launch_review_checklist(_report(tmp_path))

    assert checklist.launch_allowed is False
    assert checklist.passed is False
    assert checklist.teardown_plan is not None
    assert checklist.budget_manifest_present is True
    assert any(gate.name == "operator_acknowledged" and not gate.passed for gate in checklist.gates)


def test_launch_review_cli_writes_checklist(tmp_path) -> None:
    from decodilo.cloud.dry_run import write_report

    plan_path = tmp_path / "plan.json"
    out = tmp_path / "launch-review.json"
    write_report(plan_path, _report(tmp_path))

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "cloud",
            "launch-review",
            "--dry-run-plan",
            str(plan_path),
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert json.loads(completed.stdout)["passed"] is False
    assert json.loads(out.read_text(encoding="utf-8"))["launch_allowed"] is False

