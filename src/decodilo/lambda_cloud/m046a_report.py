"""M046A wiring report for the capacity-selected execution path."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_selected_command_preview import (
    load_lambda_capacity_selected_command_preview,
)
from decodilo.lambda_cloud.capacity_selected_execution_gate_check import (
    load_lambda_capacity_selected_execution_gate_check,
)


class LambdaM046AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    m029_run_accepts_m046_flags: bool
    execution_gate_passed: bool
    selected_candidate: str | None = None
    old_path_fallback_blocked: bool
    m039_path_fallback_blocked: bool
    command_preview_status: str | None = None
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM046AReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M046A report cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m046a_report_from_paths(
    *,
    execution_gate_check: str | Path,
    command_preview: str | Path,
) -> LambdaM046AReport:
    gate = load_lambda_capacity_selected_execution_gate_check(execution_gate_check)
    preview = load_lambda_capacity_selected_command_preview(command_preview)
    blockers = [*gate.blockers, *preview.blockers]
    preview_flags = set(preview.command_preview)
    required_flags = {
        "--capacity-selected-m046-authorization",
        "--capacity-selected-cost-risk-review",
        "--capacity-selected-operator-approval",
        "--capacity-selected-gate-check",
        "--capacity-aware-selector-output",
        "--capacity-aware-selector-authorization",
        "--capacity-aware-selector-gate-check",
        "--capacity-history",
        "--capacity-retry-policy",
        "--ssh-key-selection",
        "--response-loss-controls",
        "--m045-report",
    }
    missing_preview_flags = sorted(required_flags - preview_flags)
    if missing_preview_flags:
        blockers.extend(
            f"command_preview_missing_flag:{flag}" for flag in missing_preview_flags
        )
    flags_accepted = not missing_preview_flags
    preview_ready = (
        preview.preview_status == "ready_for_future_m046_capacity_selected_review"
        and not preview.executable
    )
    report_passed = (
        gate.gate_passed
        and preview_ready
        and gate.old_path_fallback_blocked
        and gate.m039_path_fallback_blocked
        and flags_accepted
        and not blockers
    )
    return LambdaM046AReport(
        m029_run_accepts_m046_flags=flags_accepted,
        execution_gate_passed=gate.gate_passed,
        selected_candidate=gate.selected_candidate,
        old_path_fallback_blocked=gate.old_path_fallback_blocked,
        m039_path_fallback_blocked=gate.m039_path_fallback_blocked,
        command_preview_status=preview.preview_status,
        report_passed=report_passed,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M046A is offline wiring validation only",
                    "future real launch still requires supervised M046 execution",
                    *gate.warnings,
                    *preview.warnings,
                ]
            )
        ),
    )


def load_lambda_m046a_report(path: str | Path) -> LambdaM046AReport:
    return LambdaM046AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m046a_report(path: str | Path, report: LambdaM046AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
