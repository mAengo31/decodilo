"""Final offline gate for M051 one-shot arming."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m051_execution_reviewer_bridge import (
    load_lambda_m051_execution_reviewer_bridge,
)


class LambdaM051ArmingGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    arming_gate_passed: bool
    one_shot_request_send_permitted: bool = False
    reviewer_bridge_one_shot_request_send_permitted: bool
    standing_launch_allowed: bool = False
    standing_launch_ready: bool = False
    selected_candidate: str | None = None
    selected_region: str | None = None
    no_ssh: bool = True
    no_remote_commands: bool = True
    no_package_install: bool = True
    no_training: bool = True
    max_launch_attempts: int = 1
    expires_at_utc: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_gate(self) -> LambdaM051ArmingGateCheck:
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
            or self.max_launch_attempts != 1
        ):
            raise ValueError("M051 arming gate cannot enable unsafe launch")
        if self.arming_gate_passed and (
            self.blockers or not self.reviewer_bridge_one_shot_request_send_permitted
        ):
            raise ValueError("M051 arming gate cannot pass without one-shot bridge")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_arming_gate_check_from_paths(
    *,
    reviewer_bridge: str | Path,
) -> LambdaM051ArmingGateCheck:
    bridge = load_lambda_m051_execution_reviewer_bridge(reviewer_bridge)
    blockers = list(bridge.blockers)
    if bridge.bridge_status != "reviewer_compatible_one_shot_ready":
        blockers.append("reviewer_bridge_not_ready")
    if not bridge.one_shot_request_send_permitted:
        blockers.append("one_shot_request_send_not_permitted")
    if bridge.max_launch_attempts != 1:
        blockers.append("max_launch_attempts_not_one")
    return LambdaM051ArmingGateCheck(
        arming_gate_passed=not blockers,
        reviewer_bridge_one_shot_request_send_permitted=(
            bridge.one_shot_request_send_permitted
        ),
        selected_candidate=bridge.selected_candidate,
        selected_region=bridge.selected_region,
        no_ssh=bridge.no_ssh,
        no_remote_commands=bridge.no_remote_commands,
        no_package_install=bridge.no_package_install,
        no_training=bridge.no_training,
        max_launch_attempts=bridge.max_launch_attempts,
        expires_at_utc=bridge.expires_at_utc,
        blockers=sorted(set(blockers)),
        warnings=[
            "M051 arming gate is offline and does not execute launch",
            "M051B must still run a supervised command before expiration",
        ],
    )


def load_lambda_m051_arming_gate_check(path: str | Path) -> LambdaM051ArmingGateCheck:
    return LambdaM051ArmingGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_arming_gate_check(
    path: str | Path,
    report: LambdaM051ArmingGateCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
