"""M044G flexible-selector future-review package report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.availability_first_candidate_ranker import (
    load_lambda_availability_first_candidate_ranker,
)
from decodilo.lambda_cloud.flexible_selector_authorization import (
    load_lambda_flexible_selector_authorization,
)
from decodilo.lambda_cloud.flexible_selector_command_preview import (
    load_lambda_flexible_selector_command_preview,
)
from decodilo.lambda_cloud.flexible_selector_fixed_shape_audit import (
    load_lambda_flexible_selector_fixed_shape_audit,
)
from decodilo.lambda_cloud.flexible_selector_gate_check import (
    load_lambda_flexible_selector_gate_check,
)


class LambdaM044GReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    read_only_discovery_status: str = "not_run"
    selector_without_risk_status: str | None = None
    selector_with_risk_status: str
    operator_approval_status: str | None = None
    authorization_status: str
    gate_check_status: str
    fixed_shape_audit_status: str
    command_preview_status: str
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    future_launch_candidate: bool = False
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM044GReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M044G report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m044g_report_from_paths(
    *,
    selector_output: str | Path,
    authorization: str | Path,
    gate_check: str | Path,
    fixed_shape_audit: str | Path,
    command_preview: str | Path,
    selector_without_risk: str | Path | None = None,
    read_only_discovery_status: str = "not_run",
) -> LambdaM044GReport:
    selector = load_lambda_availability_first_candidate_ranker(selector_output)
    no_risk = (
        None
        if selector_without_risk is None or not Path(selector_without_risk).exists()
        else load_lambda_availability_first_candidate_ranker(selector_without_risk)
    )
    auth = load_lambda_flexible_selector_authorization(authorization)
    gate = load_lambda_flexible_selector_gate_check(gate_check)
    audit = load_lambda_flexible_selector_fixed_shape_audit(fixed_shape_audit)
    preview = load_lambda_flexible_selector_command_preview(command_preview)
    blockers = [
        *selector.blockers,
        *auth.blockers,
        *gate.blockers,
        *audit.blockers,
        *preview.blockers,
    ]
    report_passed = (
        auth.authorization_status == "authorized_for_future_flexible_selector_launch_review"
        and gate.gate_passed
        and audit.audit_passed
        and preview.preview_status == "ready_for_future_flexible_selector_review"
        and not blockers
    )
    return LambdaM044GReport(
        read_only_discovery_status=read_only_discovery_status,
        selector_without_risk_status=None if no_risk is None else no_risk.selection_status,
        selector_with_risk_status=selector.selection_status,
        operator_approval_status=(
            None if not auth.operator_approval_ref else "approval_artifact_verified"
        ),
        authorization_status=auth.authorization_status,
        gate_check_status="passed" if gate.gate_passed else "blocked",
        fixed_shape_audit_status="passed" if audit.audit_passed else "blocked",
        command_preview_status=preview.preview_status,
        selected_candidate=auth.selected_candidate,
        selected_candidate_source=auth.selected_candidate_source,
        future_launch_candidate=report_passed,
        report_passed=report_passed,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M044G is review-only and cannot launch",
                    "future launch requires a separate supervised milestone",
                    *selector.warnings,
                    *auth.warnings,
                    *gate.warnings,
                    *audit.warnings,
                    *preview.warnings,
                ]
            )
        ),
    )


def load_lambda_m044g_report(path: str | Path) -> LambdaM044GReport:
    return LambdaM044GReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m044g_report(path: str | Path, report: LambdaM044GReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
