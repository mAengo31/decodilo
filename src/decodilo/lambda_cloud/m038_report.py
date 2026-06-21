"""M038 lower-cost M039 authorization review report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_gate_check import (
    LambdaLowerCostGateCheck,
    load_lambda_lower_cost_gate_check,
)
from decodilo.lambda_cloud.lower_cost_launch_command_preview import (
    LambdaLowerCostLaunchCommandPreview,
    load_lambda_lower_cost_launch_command_preview,
)
from decodilo.lambda_cloud.lower_cost_m039_authorization import (
    LambdaLowerCostM039Authorization,
    load_lambda_lower_cost_m039_authorization,
)


class LambdaM038Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: str
    gate_passed: bool
    command_preview_status: str
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM038Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M038 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m038_report(
    *,
    authorization: LambdaLowerCostM039Authorization,
    gate_check: LambdaLowerCostGateCheck,
    command_preview: LambdaLowerCostLaunchCommandPreview,
) -> LambdaM038Report:
    blockers = sorted(
        set(
            [
                *authorization.blockers,
                *gate_check.blockers,
                *command_preview.blockers,
            ]
        )
    )
    return LambdaM038Report(
        authorization_status=authorization.authorization_status,
        gate_passed=gate_check.gate_passed,
        command_preview_status=command_preview.preview_status,
        report_passed=authorization.authorization_status
        in {
            "authorized_for_future_m039_lower_cost_launch_attempt",
            "not_authorized",
        },
        blockers=blockers,
        warnings=[
            "M038 report is no-launch/no-termination/no-mutation",
            *authorization.warnings,
            *gate_check.warnings,
            *command_preview.warnings,
        ],
    )


def build_lambda_m038_report_from_paths(
    *,
    authorization: str | Path,
    gate_check: str | Path,
    command_preview: str | Path,
) -> LambdaM038Report:
    return build_lambda_m038_report(
        authorization=load_lambda_lower_cost_m039_authorization(authorization),
        gate_check=load_lambda_lower_cost_gate_check(gate_check),
        command_preview=load_lambda_lower_cost_launch_command_preview(command_preview),
    )


def load_lambda_m038_report(path: str | Path) -> LambdaM038Report:
    return LambdaM038Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m038_report(path: str | Path, report: LambdaM038Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
