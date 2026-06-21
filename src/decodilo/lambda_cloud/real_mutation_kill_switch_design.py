"""Review-only kill-switch and emergency teardown design for future Lambda mutation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaKillSwitchCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    criterion_id: str
    description: str
    required: bool = True


class LambdaEmergencyTeardownDesign(BaseModel):
    model_config = ConfigDict(frozen=True)

    owned_instance_id_list_required: bool = True
    termination_verification_loop_required: bool = True
    manual_emergency_command_placeholder: str = "operator-run termination procedure placeholder"
    executable_terminate_command: str | None = None
    automatic_termination_implemented: bool = False
    failure_escalation_steps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _no_executable_termination(self) -> LambdaEmergencyTeardownDesign:
        if self.executable_terminate_command:
            raise ValueError("M023 kill-switch design must not include executable termination")
        if self.automatic_termination_implemented:
            raise ValueError("M023 kill-switch design must not implement automatic termination")
        return self


class LambdaKillSwitchDesign(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    design_id: str = "lambda-kill-switch-design-m023"
    design_only: bool = True
    operator_visible_active_resources: bool = True
    resource_ledger_path_required: bool = True
    owned_instance_ids_required: bool = True
    max_runtime_deadline_required: bool = True
    budget_threshold_required: bool = True
    termination_verification_required: bool = True
    audit_log_path_required: bool = True
    no_secret_printing: bool = True
    no_automatic_termination_implementation: bool = True
    emergency_teardown: LambdaEmergencyTeardownDesign = Field(
        default_factory=lambda: LambdaEmergencyTeardownDesign(
            failure_escalation_steps=[
                "stop new work",
                "identify ledger-owned instance ids",
                "perform future reviewed termination procedure",
                "verify through read-only list/get",
                "record final audit entry",
            ]
        )
    )
    criteria: list[LambdaKillSwitchCriterion] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_design_only(self) -> LambdaKillSwitchDesign:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M023 kill-switch design cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_kill_switch_design() -> LambdaKillSwitchDesign:
    criteria = [
        LambdaKillSwitchCriterion(
            criterion_id="resource_ledger",
            description="Operator can see the resource ledger path and owned ids.",
        ),
        LambdaKillSwitchCriterion(
            criterion_id="max_runtime_deadline",
            description="A hard max runtime deadline is visible before launch.",
        ),
        LambdaKillSwitchCriterion(
            criterion_id="budget_threshold",
            description="A budget threshold is visible before launch.",
        ),
        LambdaKillSwitchCriterion(
            criterion_id="termination_verification",
            description="Termination verification loop is required.",
        ),
        LambdaKillSwitchCriterion(
            criterion_id="audit_log",
            description="Emergency action audit log path is present.",
        ),
    ]
    return LambdaKillSwitchDesign(criteria=criteria)


def load_lambda_kill_switch_design(path: str | Path) -> LambdaKillSwitchDesign:
    return LambdaKillSwitchDesign.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_kill_switch_design(path: str | Path, design: LambdaKillSwitchDesign) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(design.to_json(), encoding="utf-8")
