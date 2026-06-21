"""M051A one-shot arming bridge report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m051_arming_command_preview import (
    load_lambda_m051_arming_command_preview,
)
from decodilo.lambda_cloud.m051_arming_gate_check import (
    load_lambda_m051_arming_gate_check,
)
from decodilo.lambda_cloud.m051_execution_reviewer_bridge import (
    load_lambda_m051_execution_reviewer_bridge,
)
from decodilo.lambda_cloud.m051_one_shot_arming import (
    load_lambda_m051_one_shot_arming,
)
from decodilo.lambda_cloud.m051_operator_confirmation import (
    load_lambda_m051_operator_confirmation,
)


class LambdaM051AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_passed: bool
    operator_confirmation_status: str
    one_shot_arming_status: str
    command_binding_status: str
    artifact_binding_status: str
    reviewer_bridge_status: str
    arming_gate_status: str
    command_preview_status: str
    one_shot_request_send_permitted_in_bridge: bool
    standing_launch_ready: bool = False
    standing_launch_allowed: bool = False
    selected_candidate: str | None = None
    selected_region: str | None = None
    no_ssh: bool = True
    no_remote_commands: bool = True
    no_package_install: bool = True
    no_training: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM051AReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.standing_launch_ready
            or self.standing_launch_allowed
            or not self.no_ssh
            or not self.no_remote_commands
            or not self.no_package_install
            or not self.no_training
        ):
            raise ValueError("M051A report cannot enable launch or unsafe work")
        if self.report_passed and self.blockers:
            raise ValueError("M051A report cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051a_report_from_paths(
    *,
    operator_confirmation: str | Path,
    arming: str | Path,
    reviewer_bridge: str | Path,
    arming_gate: str | Path,
    command_preview: str | Path,
) -> LambdaM051AReport:
    confirmation = load_lambda_m051_operator_confirmation(operator_confirmation)
    arming_report = load_lambda_m051_one_shot_arming(arming)
    bridge = load_lambda_m051_execution_reviewer_bridge(reviewer_bridge)
    gate = load_lambda_m051_arming_gate_check(arming_gate)
    preview = load_lambda_m051_arming_command_preview(command_preview)
    blockers = [
        *confirmation.blockers,
        *arming_report.blockers,
        *bridge.blockers,
        *gate.blockers,
        *preview.blockers,
    ]
    if confirmation.confirmation_status != "confirmed_for_m051_one_shot_metadata_bootstrap":
        blockers.append("operator_confirmation_not_confirmed")
    if arming_report.arming_status != "armed_for_one_shot_m051_metadata_bootstrap":
        blockers.append("one_shot_arming_not_armed")
    if bridge.bridge_status != "reviewer_compatible_one_shot_ready":
        blockers.append("reviewer_bridge_not_ready")
    if not gate.arming_gate_passed:
        blockers.append("arming_gate_not_passed")
    if preview.preview_status != "ready_for_future_m051b_one_shot_metadata_bootstrap":
        blockers.append("command_preview_not_ready")
    return LambdaM051AReport(
        report_passed=not blockers,
        operator_confirmation_status=confirmation.confirmation_status,
        one_shot_arming_status=arming_report.arming_status,
        command_binding_status=(
            "passed" if bridge.command_hash and bridge.bridge_status != "not_ready" else "blocked"
        ),
        artifact_binding_status=(
            "passed"
            if bridge.artifact_binding_hash and bridge.bridge_status != "not_ready"
            else "blocked"
        ),
        reviewer_bridge_status=bridge.bridge_status,
        arming_gate_status="passed" if gate.arming_gate_passed else "blocked",
        command_preview_status=preview.preview_status,
        one_shot_request_send_permitted_in_bridge=bridge.one_shot_request_send_permitted,
        selected_candidate=bridge.selected_candidate,
        selected_region=bridge.selected_region,
        no_ssh=bridge.no_ssh and gate.no_ssh,
        no_remote_commands=bridge.no_remote_commands and gate.no_remote_commands,
        no_package_install=bridge.no_package_install and gate.no_package_install,
        no_training=bridge.no_training and gate.no_training,
        blockers=sorted(set(blockers)),
        warnings=[
            "M051A creates reviewer-compatible one-shot arming only",
            "M051A performs no Lambda API calls and no credential use",
        ],
    )


def load_lambda_m051a_report(path: str | Path) -> LambdaM051AReport:
    return LambdaM051AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m051a_report(path: str | Path, report: LambdaM051AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
