"""M044H report for capacity-history-aware flexible selection."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_history_aware_selector import (
    load_lambda_capacity_history_aware_selector,
)
from decodilo.lambda_cloud.capacity_history_selector_authorization import (
    load_lambda_capacity_history_selector_authorization,
)
from decodilo.lambda_cloud.capacity_history_selector_command_preview import (
    load_lambda_capacity_history_selector_command_preview,
)
from decodilo.lambda_cloud.capacity_history_selector_gate_check import (
    load_lambda_capacity_history_selector_gate_check,
)


class LambdaM044HReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    excluded_candidates: list[str] = Field(default_factory=list)
    same_shape_retry_required: bool = False
    same_shape_retry_acceptance_present: bool = False
    authorization_status: str
    gate_check_status: str
    command_preview_status: str
    future_launch_candidate: bool = False
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM044HReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M044H report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m044h_report_from_paths(
    *,
    selector_output: str | Path,
    authorization: str | Path,
    gate_check: str | Path,
    command_preview: str | Path,
) -> LambdaM044HReport:
    selector = load_lambda_capacity_history_aware_selector(selector_output)
    auth = load_lambda_capacity_history_selector_authorization(authorization)
    gate = load_lambda_capacity_history_selector_gate_check(gate_check)
    preview = load_lambda_capacity_history_selector_command_preview(command_preview)
    blockers = [*selector.blockers, *auth.blockers, *gate.blockers, *preview.blockers]
    report_passed = (
        auth.authorization_status
        == "authorized_for_future_capacity_history_selector_review"
        and gate.gate_passed
        and preview.preview_status == "ready_for_future_capacity_history_selector_review"
        and not blockers
    )
    return LambdaM044HReport(
        selected_candidate=auth.selected_candidate,
        selected_candidate_source=auth.selected_candidate_source,
        excluded_candidates=selector.recent_capacity_failure_excluded_candidates,
        same_shape_retry_required=selector.same_shape_retry_required,
        same_shape_retry_acceptance_present=selector.same_shape_retry_acceptance_present,
        authorization_status=auth.authorization_status,
        gate_check_status="passed" if gate.gate_passed else "blocked",
        command_preview_status=preview.preview_status,
        future_launch_candidate=report_passed,
        report_passed=report_passed,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M044H is review-only and cannot launch",
                    "future launch requires a separate supervised milestone",
                    *selector.warnings,
                    *auth.warnings,
                    *gate.warnings,
                    *preview.warnings,
                ]
            )
        ),
    )


def load_lambda_m044h_report(path: str | Path) -> LambdaM044HReport:
    return LambdaM044HReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m044h_report(path: str | Path, report: LambdaM044HReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
