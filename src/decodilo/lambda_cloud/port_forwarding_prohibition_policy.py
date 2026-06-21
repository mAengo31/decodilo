"""Port-forwarding prohibition for SSH-connectivity-only Lambda review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaPortForwardingProhibitionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    prohibition_status: str = "port_forwarding_prohibited"
    local_forward_allowed: bool = False
    remote_forward_allowed: bool = False
    dynamic_forward_allowed: bool = False
    agent_forward_allowed: bool = False
    x11_forward_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_no_forwarding(self) -> LambdaPortForwardingProhibitionPolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.local_forward_allowed
            or self.remote_forward_allowed
            or self.dynamic_forward_allowed
            or self.agent_forward_allowed
            or self.x11_forward_allowed
        ):
            raise ValueError("port-forwarding prohibition cannot allow forwarding")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_port_forwarding_prohibition_policy() -> LambdaPortForwardingProhibitionPolicy:
    return LambdaPortForwardingProhibitionPolicy(
        warnings=[
            (
                "M053 SSH connectivity-only review prohibits local, remote, "
                "dynamic, agent, and X11 forwarding"
            )
        ],
    )


def load_lambda_port_forwarding_prohibition_policy(
    path: str | Path,
) -> LambdaPortForwardingProhibitionPolicy:
    return LambdaPortForwardingProhibitionPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_port_forwarding_prohibition_policy(
    path: str | Path,
    report: LambdaPortForwardingProhibitionPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
