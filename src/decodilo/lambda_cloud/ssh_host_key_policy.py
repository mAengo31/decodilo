"""Host-key handling policy for future SSH-connectivity-only probes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHHostKeyPolicyStatus = Literal["policy_defined", "blocked"]


class LambdaSSHHostKeyPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    host_key_policy_status: LambdaSSHHostKeyPolicyStatus
    isolated_known_hosts_file: bool = True
    global_known_hosts_modified: bool = False
    strict_host_key_checking_no: bool = False
    strict_host_key_checking_policy: Literal["accept-new", "yes", "blocked"] = "accept-new"
    accept_new_for_ephemeral_instance: bool = True
    host_key_material_serialized: bool = False
    public_artifact_fingerprint_only: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaSSHHostKeyPolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("SSH host-key policy violates offline safety constraints")
        if self.host_key_policy_status == "policy_defined" and self.blockers:
            raise ValueError("passing host-key policy cannot include blockers")
        if self.host_key_policy_status == "policy_defined" and (
            self.global_known_hosts_modified
            or self.strict_host_key_checking_no
            or self.host_key_material_serialized
            or not self.isolated_known_hosts_file
            or not self.public_artifact_fingerprint_only
        ):
            raise ValueError("passing host-key policy contains unsafe evidence")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_host_key_policy(
    *,
    isolated_known_hosts_file: bool = True,
    global_known_hosts_modified: bool = False,
    strict_host_key_checking: str = "accept-new",
    host_key_material_serialized: bool = False,
) -> LambdaSSHHostKeyPolicyReport:
    blockers: list[str] = []
    policy = strict_host_key_checking.strip()
    if not isolated_known_hosts_file:
        blockers.append("isolated_known_hosts_file_required")
    if global_known_hosts_modified:
        blockers.append("global_known_hosts_must_not_be_modified")
    if policy.lower() == "no":
        blockers.append("strict_host_key_checking_no_forbidden")
    if policy not in {"accept-new", "yes"}:
        blockers.append("strict_host_key_checking_policy_invalid")
    if host_key_material_serialized:
        blockers.append("host_key_material_serialized")
    return LambdaSSHHostKeyPolicyReport(
        host_key_policy_status="policy_defined" if not blockers else "blocked",
        isolated_known_hosts_file=isolated_known_hosts_file,
        global_known_hosts_modified=global_known_hosts_modified,
        strict_host_key_checking_no=policy.lower() == "no",
        strict_host_key_checking_policy=(
            policy if policy in {"accept-new", "yes"} else "blocked"
        ),
        accept_new_for_ephemeral_instance=policy == "accept-new",
        host_key_material_serialized=host_key_material_serialized,
        blockers=sorted(set(blockers)),
        warnings=[
            "future live run must use a run-scoped known_hosts file",
            "host key material must remain out of public artifacts",
        ],
    )


def load_lambda_ssh_host_key_policy(path: str | Path) -> LambdaSSHHostKeyPolicyReport:
    return LambdaSSHHostKeyPolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_host_key_policy(
    path: str | Path,
    report: LambdaSSHHostKeyPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
