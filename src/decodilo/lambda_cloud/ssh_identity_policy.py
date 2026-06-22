"""Identity-use policy for future SSH-connectivity-only probes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_private_key_reference_policy import (
    load_lambda_ssh_private_key_reference_policy,
)

LambdaSSHIdentityPolicyStatus = Literal["policy_defined", "blocked"]


class LambdaSSHIdentityPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    identity_policy_status: LambdaSSHIdentityPolicyStatus
    identities_only_required: bool = True
    identity_file_reference_count: int = 1
    agent_identities_allowed: bool = False
    forward_agent_required_false: bool = True
    identity_path_redacted: bool = True
    raw_key_name_public: bool = False
    private_key_path_public: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaSSHIdentityPolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("SSH identity policy violates safety constraints")
        if self.identity_policy_status == "policy_defined" and self.blockers:
            raise ValueError("passing identity policy cannot include blockers")
        if self.identity_policy_status == "policy_defined" and (
            not self.identities_only_required
            or self.agent_identities_allowed
            or not self.forward_agent_required_false
            or not self.identity_path_redacted
            or self.raw_key_name_public
            or self.private_key_path_public
        ):
            raise ValueError("passing identity policy contains unsafe evidence")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_identity_policy(
    *,
    identities_only_required: bool = True,
    identity_file_reference_count: int = 1,
    agent_identities_allowed: bool = False,
    forward_agent_required_false: bool = True,
    identity_path_redacted: bool = True,
    raw_key_name_public: bool = False,
    private_key_path_public: bool = False,
    private_key_policy_status: str | None = "policy_defined",
) -> LambdaSSHIdentityPolicyReport:
    blockers: list[str] = []
    if not identities_only_required:
        blockers.append("identities_only_yes_required")
    if identity_file_reference_count != 1:
        blockers.append("exactly_one_identity_file_required")
    if agent_identities_allowed:
        blockers.append("agent_identities_forbidden")
    if not forward_agent_required_false:
        blockers.append("forward_agent_no_required")
    if not identity_path_redacted:
        blockers.append("identity_path_must_be_redacted")
    if raw_key_name_public:
        blockers.append("raw_key_name_public_forbidden")
    if private_key_path_public:
        blockers.append("private_key_path_public_forbidden")
    if private_key_policy_status not in {None, "policy_defined"}:
        blockers.append("private_key_reference_policy_not_defined")
    return LambdaSSHIdentityPolicyReport(
        identity_policy_status="policy_defined" if not blockers else "blocked",
        identities_only_required=identities_only_required,
        identity_file_reference_count=identity_file_reference_count,
        agent_identities_allowed=agent_identities_allowed,
        forward_agent_required_false=forward_agent_required_false,
        identity_path_redacted=identity_path_redacted,
        raw_key_name_public=raw_key_name_public,
        private_key_path_public=private_key_path_public,
        blockers=sorted(set(blockers)),
        warnings=["future live probe must offer exactly one redacted identity reference"],
    )


def build_lambda_ssh_identity_policy_from_path(
    private_key_policy: str | Path,
) -> LambdaSSHIdentityPolicyReport:
    policy = load_lambda_ssh_private_key_reference_policy(private_key_policy)
    return build_lambda_ssh_identity_policy(
        private_key_policy_status=policy.key_reference_policy_status,
    )


def load_lambda_ssh_identity_policy(path: str | Path) -> LambdaSSHIdentityPolicyReport:
    return LambdaSSHIdentityPolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_identity_policy(
    path: str | Path,
    report: LambdaSSHIdentityPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
