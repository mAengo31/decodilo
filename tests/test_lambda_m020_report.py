import json
import subprocess
import sys

from decodilo.lambda_cloud.api_models import LambdaInstanceType, LambdaRegion, LambdaSSHKey
from decodilo.lambda_cloud.approval_manifest import (
    LambdaHumanApprovalManifest,
    LambdaOperatorAcknowledgements,
    write_lambda_approval_manifest,
)
from decodilo.lambda_cloud.launch_plan import build_lambda_launch_plan, write_lambda_launch_plan
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.live_resource_ledger import (
    reconcile_lambda_live_resources,
    write_lambda_live_ledger_report,
)
from decodilo.lambda_cloud.m020_report import build_lambda_m020_report
from decodilo.lambda_cloud.read_only_audit import (
    LambdaReadOnlyAuditEntry,
    audit_lambda_read_only,
    write_lambda_read_only_audit_report,
)
from decodilo.lambda_cloud.teardown_plan import (
    build_lambda_teardown_plan,
    write_lambda_teardown_plan,
)
from decodilo.pricing.snapshots import (
    PriceSnapshot,
    PriceSourceType,
    SnapshotPriceRecord,
    write_price_snapshot,
)


def _write_m020_inputs(tmp_path, *, with_approval: bool = False):
    discovery = LambdaLiveDiscoveryReport(
        live_api_used=True,
        instance_types=[
            LambdaInstanceType(
                instance_type_id="gpu_8x_h100_sxm",
                name="8x H100 SXM",
                gpu_type="H100 SXM",
                gpus=8,
                regions=["us-west-1"],
            )
        ],
        regions=[LambdaRegion(region_id="us-west-1", name="US West 1")],
        ssh_keys=[LambdaSSHKey(key_id="key", name="key")],
    )
    discovery_path = tmp_path / "discovery.json"
    write_lambda_live_discovery_report(discovery_path, discovery)
    audit_path = tmp_path / "audit.json"
    write_lambda_read_only_audit_report(
        audit_path,
        audit_lambda_read_only(
            [
                LambdaReadOnlyAuditEntry(
                    operation="list_instance_types",
                    method="GET",
                    endpoint="/instance-types",
                    allowed=True,
                    status_code=200,
                    live_api_used=True,
                )
            ]
        ),
    )
    plan = build_lambda_launch_plan(
        run_id="run",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=0.5,
        max_run_budget=50,
        ssh_key_ref="key",
        price_snapshot_ref="prices.json",
    ).model_copy(update={"budget_manifest_ref": "budget.json"})
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
    snapshot = PriceSnapshot(
        snapshot_id="snap",
        provider="lambda",
        captured_at_utc="2026-06-16T00:00:00Z",
        source_type=PriceSourceType.MANUAL_JSON,
        source_sha256="0" * 64,
        is_sample_data=False,
        records=[
            SnapshotPriceRecord(
                provider="lambda",
                instance_type="gpu_8x_h100_sxm",
                gpu_type="H100 SXM",
                gpus_per_instance=8,
                region="sample-offline",
                price_per_gpu_hour=2.5,
                price_per_instance_hour=20,
                captured_at_utc="2026-06-16T00:00:00Z",
                record_id="price-0",
            )
        ],
    )
    price_path = tmp_path / "prices.json"
    write_price_snapshot(price_path, snapshot)
    approval_path = None
    if with_approval:
        approval = LambdaHumanApprovalManifest(
            approval_id="approved",
            operator_acknowledgements=LambdaOperatorAcknowledgements(
                understands_billable_action=True,
                understands_termination_required=True,
                understands_budget_limit=True,
                understands_no_background_work=True,
                understands_no_production_training=True,
                understands_launch_not_enabled_yet=True,
            ),
            approved_instance_type="gpu_8x_h100_sxm",
            approved_region="us-west-1",
            approved_gpu_type="H100 SXM",
            approved_gpus_per_instance=8,
            approval_status="approved_for_future_fake_launch_lifecycle",
        )
        approval_path = tmp_path / "approval.json"
        write_lambda_approval_manifest(approval_path, approval)
    return (
        discovery_path,
        audit_path,
        ledger_path,
        plan_path,
        teardown_path,
        price_path,
        approval_path,
    )


def test_lambda_m020_report_builds_from_fake_evidence(tmp_path) -> None:
    inputs = _write_m020_inputs(tmp_path)

    report = build_lambda_m020_report(
        discovery_report=inputs[0],
        read_only_audit=inputs[1],
        ledger=inputs[2],
        launch_plan=inputs[3],
        teardown_plan=inputs[4],
        price_snapshot=inputs[5],
        credits=100,
        max_run_budget=50,
        planned_hours=0.5,
        safety_buffer_percentage=15,
    )

    assert report.price_reconciliation.price_reconciliation_passed is True
    assert report.approval_gate_report.approval_passed is False
    assert report.launch_allowed is False
    assert json.loads(report.to_json())["billable_action_performed"] is False


def test_lambda_m020_report_reflects_fake_lifecycle_approval(tmp_path) -> None:
    inputs = _write_m020_inputs(tmp_path, with_approval=True)

    report = build_lambda_m020_report(
        discovery_report=inputs[0],
        read_only_audit=inputs[1],
        ledger=inputs[2],
        launch_plan=inputs[3],
        teardown_plan=inputs[4],
        price_snapshot=inputs[5],
        credits=100,
        max_run_budget=50,
        planned_hours=0.5,
        safety_buffer_percentage=15,
        approval_manifest=inputs[6],
    )

    assert report.approval_gate_report.approval_passed is True
    assert report.readiness_summary.future_fake_launch_lifecycle_candidate is True
    assert report.readiness_summary.future_real_launch_candidate is False


def test_lambda_m020_cli_reconcile_and_summary(tmp_path) -> None:
    inputs = _write_m020_inputs(tmp_path, with_approval=True)
    out = tmp_path / "m020.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "m020-reconcile",
            "--discovery-report",
            str(inputs[0]),
            "--read-only-audit",
            str(inputs[1]),
            "--ledger",
            str(inputs[2]),
            "--launch-plan",
            str(inputs[3]),
            "--teardown-plan",
            str(inputs[4]),
            "--price-snapshot",
            str(inputs[5]),
            "--credits",
            "100",
            "--max-run-budget",
            "50",
            "--planned-hours",
            "0.5",
            "--safety-buffer-percentage",
            "15",
            "--approval-manifest",
            str(inputs[6]),
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "readiness-summary",
            "--m020-report",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout)["launch_allowed"] is False
    assert json.loads(summary.stdout)["future_real_launch_candidate"] is False


def test_lambda_approval_template_cli(tmp_path) -> None:
    out = tmp_path / "approval.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "approval-template",
            "--instance-type",
            "gpu_8x_h100_sxm",
            "--region",
            "us-west-1",
            "--gpu-type",
            "H100 SXM",
            "--gpus-per-instance",
            "8",
            "--max-budget",
            "50",
            "--max-runtime-minutes",
            "30",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout)["approval_status"] == "incomplete"
    assert json.loads(out.read_text(encoding="utf-8"))["launch_allowed"] is False
