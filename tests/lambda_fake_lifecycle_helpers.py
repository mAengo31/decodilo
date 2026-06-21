from __future__ import annotations

from pathlib import Path
from typing import Any

from test_lambda_m020_report import _write_m020_inputs

from decodilo.lambda_cloud.approval_manifest import (
    LambdaHumanApprovalManifest,
    LambdaOperatorAcknowledgements,
    write_lambda_approval_manifest,
)
from decodilo.lambda_cloud.m020_report import (
    LambdaM020ReadinessReport,
    build_lambda_m020_report,
    write_lambda_m020_report,
)


def write_approved_m020(
    tmp_path: Path,
    *,
    max_run_budget: float = 50.0,
    with_approval: bool = True,
    report_updates: dict[str, Any] | None = None,
) -> tuple[LambdaM020ReadinessReport, Path, Path | None]:
    inputs = _write_m020_inputs(tmp_path, with_approval=with_approval)
    report = build_lambda_m020_report(
        discovery_report=inputs[0],
        read_only_audit=inputs[1],
        ledger=inputs[2],
        launch_plan=inputs[3],
        teardown_plan=inputs[4],
        price_snapshot=inputs[5],
        credits=100,
        max_run_budget=max_run_budget,
        planned_hours=0.5,
        safety_buffer_percentage=15,
        approval_manifest=inputs[6],
    )
    if report_updates:
        report = report.model_copy(update=report_updates)
    path = tmp_path / "m020.json"
    write_lambda_m020_report(path, report)
    return report, path, inputs[6]


def write_incomplete_approval(tmp_path: Path) -> Path:
    approval = LambdaHumanApprovalManifest(
        approval_id="incomplete",
        operator_acknowledgements=LambdaOperatorAcknowledgements(),
        approved_instance_type="gpu_8x_h100_sxm",
        approved_region="us-west-1",
        approved_gpu_type="H100 SXM",
        approved_gpus_per_instance=8,
        approval_status="incomplete",
    )
    path = tmp_path / "approval-incomplete.json"
    write_lambda_approval_manifest(path, approval)
    return path
