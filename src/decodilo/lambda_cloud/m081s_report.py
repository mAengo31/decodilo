"""Aggregate M081S closeout and M081R2 retry-prep report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_artifact_parser import (
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
    load_diloco_artifact_parser_report,
)
from decodilo.lambda_cloud.diloco_smoke_attempt_closeout import (
    load_lambda_diloco_smoke_attempt_closeout,
)
from decodilo.lambda_cloud.m081r2_diloco_synthetic_authorization import (
    load_lambda_m081r2_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.m081r2_diloco_synthetic_runbook_preview import (
    load_lambda_m081r2_diloco_synthetic_runbook_preview,
)
from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
    LEARNER_SYNCER_DECLARED_ARTIFACT_PATH,
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
    load_lambda_remote_vslice_manifest_artifact_policy,
)


class LambdaM081SReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M081S"
    report_passed: bool
    m081r_closeout_status: str
    command_passed: bool
    artifact_capture_blocked: bool
    manifest_declared_artifact_policy_fixed: bool
    supported_declared_paths: list[str] = Field(default_factory=list)
    parser_fixture_status: str
    m081r2_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM081SReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M081S report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M081S report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m081s_report_from_paths(
    *,
    attempt_closeout: str | Path,
    manifest_artifact_policy: str | Path,
    parser_fixture_report: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM081SReport:
    closeout = load_lambda_diloco_smoke_attempt_closeout(attempt_closeout)
    policy = load_lambda_remote_vslice_manifest_artifact_policy(
        manifest_artifact_policy
    )
    parser = load_diloco_artifact_parser_report(parser_fixture_report)
    auth = load_lambda_m081r2_diloco_synthetic_authorization(authorization)
    preview = load_lambda_m081r2_diloco_synthetic_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("m081r_attempt_closeout_not_succeeded")
    if policy.policy_status != "manifest_artifact_policy_defined":
        blockers.extend(policy.blockers or ["manifest_artifact_policy_not_defined"])
    if not {
        RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
        LEARNER_SYNCER_DECLARED_ARTIFACT_PATH,
        DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
    }.issubset(set(policy.supported_declared_paths)):
        blockers.append("supported_declared_paths_missing_required_artifact")
    if parser.parse_status != "parsed_safe_diloco_smoke_artifact":
        blockers.append("diloco_artifact_parser_fixture_not_safe")
    if (
        parser.parsed_summary
        and parser.parsed_summary.get("optimization_fidelity") == "full_diloco"
        and parser.parsed_summary.get("inner_optimizer_semantics") != "adamw"
    ):
        blockers.append("diloco_artifact_parser_overclaimed_optimizer_fidelity")
    if (
        auth.authorization_status
        != "authorized_for_future_m081r2_diloco_synthetic_retry"
    ):
        blockers.append("m081r2_not_authorized")
    if (
        preview.preview_status
        != "ready_for_future_m081r2_diloco_synthetic_retry_review"
    ):
        blockers.append("m081r2_runbook_preview_not_ready")
    return LambdaM081SReport(
        report_passed=not blockers,
        m081r_closeout_status=closeout.closeout_status,
        command_passed=closeout.diloco_smoke_command_passed,
        artifact_capture_blocked=(
            closeout.artifact_capture_status == "blocked_undeclared_artifact_path"
        ),
        manifest_declared_artifact_policy_fixed=(
            policy.policy_status == "manifest_artifact_policy_defined"
            and policy.diloco_smoke_declared_artifact_supported
        ),
        supported_declared_paths=policy.supported_declared_paths,
        parser_fixture_status=parser.parse_status,
        m081r2_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=closeout.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=[
            "M081S is offline; M081R2 still requires fresh supervised approval",
        ],
    )


def load_lambda_m081s_report(path: str | Path) -> LambdaM081SReport:
    return LambdaM081SReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m081s_report(path: str | Path, report: LambdaM081SReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
