"""Preflight gate for fake Lambda lifecycle rehearsal."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.approval_manifest import (
    LambdaHumanApprovalManifest,
    load_lambda_approval_manifest,
)
from decodilo.lambda_cloud.fake_lifecycle_safety import validate_fake_lifecycle_safety
from decodilo.lambda_cloud.launch_plan import load_lambda_launch_plan
from decodilo.lambda_cloud.m020_report import (
    LambdaM020ReadinessReport,
    load_lambda_m020_report,
)


class FakeLambdaLifecyclePreflightReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    fake_lifecycle_only: bool = True
    real_launch_disabled: bool = True
    real_mutation_disabled: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_fake_lambda_lifecycle_preflight(
    *,
    m020_report: str | Path | LambdaM020ReadinessReport,
    approval_manifest: str | Path | LambdaHumanApprovalManifest,
) -> FakeLambdaLifecyclePreflightReport:
    m020 = (
        m020_report
        if isinstance(m020_report, LambdaM020ReadinessReport)
        else load_lambda_m020_report(m020_report)
    )
    approval = (
        approval_manifest
        if isinstance(approval_manifest, LambdaHumanApprovalManifest)
        else load_lambda_approval_manifest(approval_manifest)
    )
    plan = load_lambda_launch_plan(m020.launch_plan_ref)
    safety = validate_fake_lifecycle_safety(
        m020_report=m020,
        approval_manifest=approval,
        launch_plan=plan,
        fake_mode=True,
    )
    errors = [*safety.errors]
    warnings = [*safety.warnings]
    if not m020.live_api_used:
        warnings.append("M020 report did not use live discovery evidence")
    if not m020.read_operations:
        errors.append("read-only audit evidence is missing")
    if not m020.teardown_plan_ref:
        errors.append("teardown plan is missing")
    return FakeLambdaLifecyclePreflightReport(
        passed=not errors,
        warnings=warnings,
        errors=errors,
    )


def write_fake_lambda_lifecycle_preflight_report(
    path: str | Path,
    report: FakeLambdaLifecyclePreflightReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
