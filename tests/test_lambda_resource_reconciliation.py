import json

from decodilo.lambda_cloud.api_models import LambdaImage, LambdaInstance, LambdaRegion, LambdaSSHKey
from decodilo.lambda_cloud.launch_plan import build_lambda_launch_plan, write_lambda_launch_plan
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.live_resource_ledger import (
    reconcile_lambda_live_resources,
    write_lambda_live_ledger_report,
)
from decodilo.lambda_cloud.resource_reconciliation import reconcile_lambda_resources
from decodilo.lambda_cloud.teardown_plan import (
    build_lambda_teardown_plan,
    write_lambda_teardown_plan,
)


def _write_resource_inputs(tmp_path, *, unmanaged: bool = False, ssh_keys=None):
    discovery = LambdaLiveDiscoveryReport(
        live_api_used=True,
        regions=[LambdaRegion(region_id="us-west-1", name="US West 1")],
        images=[LambdaImage(image_id="img", name="img")],
        ssh_keys=ssh_keys if ssh_keys is not None else [LambdaSSHKey(key_id="key", name="key")],
        instances=[
            LambdaInstance(
                instance_id="i-unmanaged" if unmanaged else "i-managed",
                status="running",
                tags={} if unmanaged else {"decodilo_run_id": "run"},
            )
        ],
    )
    discovery_path = tmp_path / "discovery.json"
    write_lambda_live_discovery_report(discovery_path, discovery)
    plan = build_lambda_launch_plan(
        run_id="run",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=0.5,
        max_run_budget=50,
        image="img",
        ssh_key_ref="key",
    )
    plan_path = tmp_path / "plan.json"
    write_lambda_launch_plan(plan_path, plan)
    teardown = build_lambda_teardown_plan(
        run_id="run",
        planned_node_ids=[node.node_id for node in plan.nodes],
    )
    teardown_path = tmp_path / "teardown.json"
    write_lambda_teardown_plan(teardown_path, teardown)
    ledger = reconcile_lambda_live_resources(discovery=discovery, launch_plan=plan)
    ledger_path = tmp_path / "ledger.json"
    write_lambda_live_ledger_report(ledger_path, ledger)
    return discovery_path, ledger_path, plan_path, teardown_path


def test_lambda_resource_reconciliation_clean_fake_discovery_passes(tmp_path) -> None:
    discovery, ledger, plan, teardown = _write_resource_inputs(tmp_path)

    report = reconcile_lambda_resources(
        discovery_report=discovery,
        ledger_report=ledger,
        launch_plan=plan,
        teardown_plan=teardown,
    )

    assert report.resource_reconciliation_passed is True
    assert report.manual_review_required is False
    assert json.loads(report.to_json())["launch_ready"] is False


def test_lambda_resource_reconciliation_flags_unmanaged_running_instance(tmp_path) -> None:
    discovery, ledger, plan, teardown = _write_resource_inputs(tmp_path, unmanaged=True)

    report = reconcile_lambda_resources(
        discovery_report=discovery,
        ledger_report=ledger,
        launch_plan=plan,
        teardown_plan=teardown,
    )

    assert report.manual_review_required is True
    assert report.unmanaged_billable_instances == 1
    assert "terminate" not in report.to_json().lower()


def test_lambda_resource_reconciliation_fails_missing_ssh_key(tmp_path) -> None:
    discovery, ledger, plan, teardown = _write_resource_inputs(tmp_path, ssh_keys=[])

    report = reconcile_lambda_resources(
        discovery_report=discovery,
        ledger_report=ledger,
        launch_plan=plan,
        teardown_plan=teardown,
    )

    assert report.resource_reconciliation_passed is False
    assert "missing_ssh_key" in report.planned_resource_conflicts
