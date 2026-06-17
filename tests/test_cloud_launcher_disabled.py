import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError
from decodilo.pricing.registry import import_json_snapshot


def test_disabled_cloud_launcher_always_refuses_launch(tmp_path) -> None:
    from decodilo.cloud.lambda_plan import LambdaDryRunPlanner

    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    report = LambdaDryRunPlanner().build_plan(
        run_id="disabled-launch",
        price_snapshot_path=snapshot_path,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        nodes=1,
        hours=1,
        credits=7500,
        max_run_budget=1000,
    )

    with pytest.raises(LaunchDisabledError, match="disabled"):
        DisabledCloudLauncher().launch(LaunchRequest(plan=report.plan))


def test_cloud_launch_disabled_cli_exits_zero_only_when_launch_refused(tmp_path) -> None:
    import json
    import subprocess
    import sys

    from decodilo.cloud.dry_run import write_report
    from decodilo.cloud.lambda_plan import LambdaDryRunPlanner

    snapshot_path = tmp_path / "snapshot.json"
    plan_path = tmp_path / "plan.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    write_report(
        plan_path,
        LambdaDryRunPlanner().build_plan(
            run_id="disabled-launch-cli",
            price_snapshot_path=snapshot_path,
            gpu_type="H100 SXM",
            gpus_per_instance=8,
            nodes=1,
            hours=1,
            credits=7500,
            max_run_budget=1000,
        ),
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "cloud",
            "launch-disabled-test",
            "--dry-run-plan",
            str(plan_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert json.loads(completed.stdout)["launch_disabled"] is True

