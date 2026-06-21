"""M054A preparation report for future SSH-connectivity-only execution."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_connectivity_command_preview import (
    load_lambda_ssh_connectivity_command_preview,
)
from decodilo.lambda_cloud.ssh_connectivity_execution_plan import (
    load_lambda_ssh_connectivity_execution_plan,
)
from decodilo.lambda_cloud.ssh_connectivity_no_exec_audit import (
    load_lambda_ssh_connectivity_no_exec_audit,
)
from decodilo.lambda_cloud.ssh_connectivity_reviewer_bridge import (
    load_lambda_ssh_connectivity_reviewer_bridge,
)
from decodilo.lambda_cloud.ssh_connectivity_static_validator import (
    load_lambda_ssh_connectivity_static_validation,
)


class LambdaM054AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    execution_plan_status: str
    static_validation_status: str
    reviewer_bridge_status: str
    no_exec_audit_status: str
    command_preview_status: str
    future_m054b_cli_flags_accepted: bool
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM054AReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M054A report cannot enable launch or SSH")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m054a_report_from_paths(
    *,
    execution_plan: str | Path,
    static_validation: str | Path,
    reviewer_bridge: str | Path,
    no_exec_audit: str | Path,
    command_preview: str | Path,
) -> LambdaM054AReport:
    plan = load_lambda_ssh_connectivity_execution_plan(execution_plan)
    static = load_lambda_ssh_connectivity_static_validation(static_validation)
    bridge = load_lambda_ssh_connectivity_reviewer_bridge(reviewer_bridge)
    audit = load_lambda_ssh_connectivity_no_exec_audit(no_exec_audit)
    preview = load_lambda_ssh_connectivity_command_preview(command_preview)
    blockers = [
        *plan.blockers,
        *static.blockers,
        *bridge.blockers,
        *audit.blockers,
        *preview.blockers,
    ]
    report_passed = (
        plan.plan_status == "plan_defined"
        and static.static_validation_passed
        and bridge.bridge_status == "reviewer_compatible_one_shot_ready"
        and audit.audit_passed
        and preview.preview_status == "ready_for_future_m054b_ssh_connectivity_review"
        and not blockers
    )
    return LambdaM054AReport(
        execution_plan_status=plan.plan_status,
        static_validation_status="passed" if static.static_validation_passed else "blocked",
        reviewer_bridge_status=bridge.bridge_status,
        no_exec_audit_status="passed" if audit.audit_passed else "blocked",
        command_preview_status=preview.preview_status,
        future_m054b_cli_flags_accepted=True,
        report_passed=report_passed,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M054A prepares a future SSH connectivity review only",
                    "M054B remains a separate supervised and billable milestone",
                    *plan.warnings,
                    *static.warnings,
                    *bridge.warnings,
                    *audit.warnings,
                    *preview.warnings,
                ]
            )
        ),
    )


def load_lambda_m054a_report(path: str | Path) -> LambdaM054AReport:
    return LambdaM054AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m054a_report(path: str | Path, report: LambdaM054AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
