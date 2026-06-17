import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_preflight import run_cloud_preflight
from decodilo.cloud.launch_review import (
    build_launch_review_checklist,
    write_launch_review_checklist,
)
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError
from decodilo.pricing.registry import import_json_snapshot

pytestmark = pytest.mark.cloud_disabled


def test_cloud_preflight_and_launcher_remain_disabled(tmp_path) -> None:
    from decodilo.cloud.dry_run import write_report
    from decodilo.cloud.lambda_plan import LambdaDryRunPlanner

    snapshot_path = tmp_path / "snapshot.json"
    plan_path = tmp_path / "plan.json"
    review_path = tmp_path / "launch-review.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    report = LambdaDryRunPlanner().build_plan(
        run_id="cloud-disabled-m011",
        price_snapshot_path=snapshot_path,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        nodes=1,
        hours=1,
        credits=7500,
        max_run_budget=1000,
    )
    write_report(plan_path, report)
    write_launch_review_checklist(
        review_path,
        build_launch_review_checklist(report=report, operator_acknowledged=False),
    )

    preflight = run_cloud_preflight(
        dry_run_plan=plan_path,
        launch_review_path=review_path,
    )

    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False
    assert preflight.resource_limit_summary["remote_backend_enabled"] is False
    assert any("cloud launch is disabled" in warning for warning in preflight.warnings)
    with pytest.raises(LaunchDisabledError):
        DisabledCloudLauncher().launch(LaunchRequest(plan=report.plan))
