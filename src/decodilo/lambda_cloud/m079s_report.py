"""Aggregate M079S closeout and M079R2 retry-prep report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.learner_syncer_artifact_parser import (
    load_learner_syncer_artifact_parser_report,
)
from decodilo.lambda_cloud.learner_syncer_smoke_attempt_closeout import (
    load_lambda_learner_syncer_smoke_attempt_closeout,
)
from decodilo.lambda_cloud.m079r2_next_synthetic_experiment_authorization import (
    load_lambda_m079r2_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m079r2_next_synthetic_experiment_runbook_preview import (
    load_lambda_m079r2_next_synthetic_experiment_runbook_preview,
)
from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
    load_lambda_remote_vslice_declared_artifact_policy,
)


class LambdaM079SReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M079S"
    report_passed: bool
    m079r_closeout_status: str
    command_passed: bool
    artifact_capture_blocked: bool
    declared_artifact_policy_fixed: bool
    parser_fixture_status: str
    m079r2_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM079SReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M079S report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M079S report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m079s_report_from_paths(
    *,
    attempt_closeout: str | Path,
    declared_artifact_policy: str | Path,
    parser_fixture_report: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM079SReport:
    closeout = load_lambda_learner_syncer_smoke_attempt_closeout(attempt_closeout)
    policy = load_lambda_remote_vslice_declared_artifact_policy(declared_artifact_policy)
    parser = load_learner_syncer_artifact_parser_report(parser_fixture_report)
    auth = load_lambda_m079r2_next_synthetic_experiment_authorization(authorization)
    preview = load_lambda_m079r2_next_synthetic_experiment_runbook_preview(
        runbook_preview
    )
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("m079r_attempt_closeout_not_succeeded")
    if policy.policy_status != "policy_defined":
        blockers.extend(policy.blockers or ["declared_artifact_policy_not_defined"])
    if parser.parse_status != "parsed_safe_learner_syncer_smoke_artifact":
        blockers.append("learner_syncer_artifact_parser_fixture_not_safe")
    if (
        auth.authorization_status
        != "authorized_for_future_m079r2_next_synthetic_experiment_retry"
    ):
        blockers.append("m079r2_not_authorized")
    if (
        preview.preview_status
        != "ready_for_future_m079r2_next_synthetic_experiment_retry_review"
    ):
        blockers.append("m079r2_runbook_preview_not_ready")
    return LambdaM079SReport(
        report_passed=not blockers,
        m079r_closeout_status=closeout.closeout_status,
        command_passed=closeout.learner_syncer_smoke_command_passed,
        artifact_capture_blocked=(
            closeout.artifact_capture_status == "blocked_undeclared_artifact_path"
        ),
        declared_artifact_policy_fixed=policy.policy_status == "policy_defined",
        parser_fixture_status=parser.parse_status,
        m079r2_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=closeout.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=[
            "M079S is offline; M079R2 still requires fresh supervised approval",
        ],
    )


def load_lambda_m079s_report(path: str | Path) -> LambdaM079SReport:
    return LambdaM079SReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m079s_report(path: str | Path, report: LambdaM079SReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
