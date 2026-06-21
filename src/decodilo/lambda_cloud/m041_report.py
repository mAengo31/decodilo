"""M041 catalog availability risk decision report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_availability_command_preview import (
    load_lambda_catalog_availability_command_preview,
)
from decodilo.lambda_cloud.catalog_availability_gate_check import (
    load_lambda_catalog_availability_gate_check,
)
from decodilo.lambda_cloud.catalog_availability_m042_authorization import (
    load_lambda_catalog_availability_m042_authorization,
)
from decodilo.lambda_cloud.catalog_availability_operator_decision import (
    load_lambda_catalog_availability_operator_decision,
)
from decodilo.lambda_cloud.catalog_availability_risk_acceptance import (
    load_lambda_catalog_availability_risk_acceptance,
)
from decodilo.lambda_cloud.wait_for_live_availability_plan import (
    load_lambda_wait_for_live_availability_plan,
)


class LambdaM041Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    risk_acceptance_status: str
    operator_decision_status: str
    m042_authorization_status: str | None = None
    gate_check_status: str | None = None
    command_preview_status: str | None = None
    wait_plan_status: str | None = None
    future_m042_candidate: bool
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM041Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M041 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m041_report_from_paths(
    *,
    risk_acceptance: str | Path,
    operator_decision: str | Path,
    m042_authorization: str | Path | None = None,
    gate_check: str | Path | None = None,
    command_preview: str | Path | None = None,
    wait_plan: str | Path | None = None,
) -> LambdaM041Report:
    risk = load_lambda_catalog_availability_risk_acceptance(risk_acceptance)
    decision = load_lambda_catalog_availability_operator_decision(operator_decision)
    blockers = [*risk.blockers, *decision.blockers]
    warnings = [
        "M041 is review-only and cannot authorize launch execution",
        "M042 remains a separately supervised billable milestone if pursued",
    ]
    auth_status = None
    gate_status = None
    preview_status = None
    wait_status = None
    future_candidate = False
    if m042_authorization is not None:
        auth = load_lambda_catalog_availability_m042_authorization(m042_authorization)
        auth_status = auth.authorization_status
        blockers.extend(auth.blockers)
        warnings.extend(auth.warnings)
        future_candidate = (
            auth.authorization_status
            == "authorized_for_future_m042_catalog_availability_launch_review"
        )
    if gate_check is not None:
        gate = load_lambda_catalog_availability_gate_check(gate_check)
        gate_status = "passed" if gate.gate_passed else "blocked"
        blockers.extend(gate.blockers)
        warnings.extend(gate.warnings)
        future_candidate = future_candidate and gate.gate_passed
    if command_preview is not None:
        preview = load_lambda_catalog_availability_command_preview(command_preview)
        preview_status = preview.preview_status
        blockers.extend(preview.blockers)
        warnings.extend(preview.warnings)
        future_candidate = (
            future_candidate and preview.preview_status == "ready_for_future_m042"
        )
    if wait_plan is not None:
        wait = load_lambda_wait_for_live_availability_plan(wait_plan)
        wait_status = wait.plan_status
        blockers.extend(wait.blockers)
        warnings.extend(wait.warnings)
    report_passed = (
        future_candidate
        if decision.decision_status
        == "accept_catalog_availability_risk_for_future_m042_review"
        else wait_status == "wait_for_live_availability"
    )
    return LambdaM041Report(
        risk_acceptance_status=risk.acceptance_status,
        operator_decision_status=decision.decision_status,
        m042_authorization_status=auth_status,
        gate_check_status=gate_status,
        command_preview_status=preview_status,
        wait_plan_status=wait_status,
        future_m042_candidate=future_candidate,
        report_passed=report_passed and not blockers,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
    )


def load_lambda_m041_report(path: str | Path) -> LambdaM041Report:
    return LambdaM041Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m041_report(path: str | Path, report: LambdaM041Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
