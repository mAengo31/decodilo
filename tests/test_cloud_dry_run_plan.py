import json
import subprocess
import sys

import pytest

from decodilo.cloud.lambda_plan import LambdaDryRunPlanner
from decodilo.cloud.launch_plan import load_cloud_dry_run_report
from decodilo.errors import PricingAmbiguityError
from decodilo.pricing.registry import import_json_snapshot


def test_lambda_dry_run_plan_from_fresh_manual_snapshot(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot = import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )

    report = LambdaDryRunPlanner().build_plan(
        run_id="dry-run",
        price_snapshot_path=snapshot_path,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        nodes=1,
        hours=2,
        credits=7500,
        max_run_budget=1000,
        region="us-west-1",
    )

    assert report.plan.launch_allowed is False
    assert report.plan.price_snapshot_id == snapshot.snapshot_id
    assert report.plan.selected_price_record_id
    assert report.plan.base_estimated_cost == 39.84
    assert report.validation_errors == []
    assert "LAMBDA_API_KEY" in report.plan.secrets_required
    assert "AKIA" not in report.to_json()


@pytest.mark.integration
def test_cloud_dry_run_cli_writes_and_validates_plan(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    out = tmp_path / "dry-run.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "cloud",
            "dry-run",
            "lambda",
            "--price-snapshot",
            str(snapshot_path),
            "--gpu-type",
            "H100 SXM",
            "--gpus-per-instance",
            "8",
            "--nodes",
            "1",
            "--hours",
            "2",
            "--credits",
            "7500",
            "--max-run-budget",
            "1000",
            "--region",
            "us-west-1",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    summary = json.loads(completed.stdout)
    assert summary["launch_allowed"] is False
    assert out.exists()
    assert load_cloud_dry_run_report(out).plan.launch_allowed is False

    validate = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "cloud", "dry-run", "validate", str(out)],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert json.loads(validate.stdout)["passed"] is True


def test_sample_snapshot_rejected_by_default(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=True,
    )

    with pytest.raises(PricingAmbiguityError, match="sample"):
        LambdaDryRunPlanner().build_plan(
            run_id="dry-run",
            price_snapshot_path=snapshot_path,
            gpu_type="H100 SXM",
            gpus_per_instance=8,
            nodes=1,
            hours=2,
            credits=7500,
            max_run_budget=1000,
        )
