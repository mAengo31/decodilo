from decodilo.lambda_cloud.approval_gate import evaluate_lambda_approval_gate
from decodilo.lambda_cloud.approval_manifest import (
    LambdaHumanApprovalManifest,
    LambdaOperatorAcknowledgements,
)
from decodilo.lambda_cloud.launch_plan import build_lambda_launch_plan


def _plan():
    return build_lambda_launch_plan(
        run_id="run",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=0.5,
        max_run_budget=50,
    )


def test_lambda_approval_gate_incomplete_until_acknowledged() -> None:
    report = evaluate_lambda_approval_gate(approval_manifest=None, launch_plan=_plan())

    assert report.approval_passed is False
    assert report.approval_status == "not_requested"
    assert "missing_human_approval" in report.errors


def test_lambda_approval_gate_fake_lifecycle_does_not_enable_launch() -> None:
    manifest = LambdaHumanApprovalManifest(
        approval_id="ok",
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

    report = evaluate_lambda_approval_gate(approval_manifest=manifest, launch_plan=_plan())

    assert report.approval_passed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lambda_approval_gate_rejects_limits_above_policy() -> None:
    manifest = LambdaHumanApprovalManifest(
        approval_id="too-high",
        approved_instance_type="gpu_8x_h100_sxm",
        approved_region="us-west-1",
        approved_gpu_type="H100 SXM",
        approved_gpus_per_instance=8,
        approved_max_budget=100,
        approval_status="approved_for_future_fake_launch_lifecycle",
    )

    report = evaluate_lambda_approval_gate(approval_manifest=manifest, launch_plan=_plan())

    assert report.approval_passed is False
    assert any("approved_max_budget" in item for item in report.mismatched_limits)
