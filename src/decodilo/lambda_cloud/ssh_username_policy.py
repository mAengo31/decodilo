"""Username policy for future SSH-connectivity-only probes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHUsernamePolicyStatus = Literal["policy_defined", "blocked"]


class LambdaSSHUsernamePolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    username_policy_status: LambdaSSHUsernamePolicyStatus
    selected_username: str
    source: Literal["lambda_docs_default", "operator_override", "unknown"]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHUsernamePolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("SSH username policy cannot enable launch")
        if self.username_policy_status == "policy_defined" and self.blockers:
            raise ValueError("passing username policy cannot include blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_username_policy(
    *,
    username: str | None = "ubuntu",
    source: Literal["lambda_docs_default", "operator_override", "unknown"] = (
        "lambda_docs_default"
    ),
    root_override_approved: bool = False,
) -> LambdaSSHUsernamePolicyReport:
    selected = (username or "").strip()
    blockers: list[str] = []
    warnings: list[str] = []
    if not selected:
        blockers.append("ssh_username_missing")
    if selected == "root" and not root_override_approved:
        blockers.append("root_username_requires_operator_override")
    if source == "unknown":
        warnings.append("username source is unknown; future live review must make it explicit")
    return LambdaSSHUsernamePolicyReport(
        username_policy_status="policy_defined" if not blockers else "blocked",
        selected_username=selected,
        source=source,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def load_lambda_ssh_username_policy(path: str | Path) -> LambdaSSHUsernamePolicyReport:
    return LambdaSSHUsernamePolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_username_policy(
    path: str | Path,
    report: LambdaSSHUsernamePolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
