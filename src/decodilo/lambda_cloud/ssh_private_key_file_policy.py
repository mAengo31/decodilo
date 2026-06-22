"""Private key file policy for future SSH-connectivity-only probes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHPrivateKeyFilePolicyStatus = Literal["policy_defined", "blocked"]

_PRIVATE_MARKERS = (
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "BEGIN EC PRIVATE KEY",
    "PRIVATE KEY-----",
)
_PUBLIC_MARKERS = ("ssh-rsa ", "ssh-ed25519 ", "ecdsa-sha2-")


class LambdaSSHPrivateKeyFilePolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    private_key_file_policy_status: LambdaSSHPrivateKeyFilePolicyStatus
    permission_policy: str = "0600_or_stricter"
    operator_approved_private_key_reference_required: bool = True
    raw_key_material_serialized: bool = False
    public_key_material_serialized: bool = False
    private_key_path_public: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaSSHPrivateKeyFilePolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.private_key_path_public
        ):
            raise ValueError("private key file policy cannot expose key material")
        if self.private_key_file_policy_status == "policy_defined" and self.blockers:
            raise ValueError("passing private key file policy cannot include blockers")
        if self.private_key_file_policy_status == "policy_defined" and (
            self.raw_key_material_serialized or self.public_key_material_serialized
        ):
            raise ValueError("passing private key file policy cannot detect key material")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_private_key_file_policy(
    *,
    checked_mode: int | None = None,
    serialized_value: str = "",
    private_key_path_public: bool = False,
) -> LambdaSSHPrivateKeyFilePolicyReport:
    blockers: list[str] = []
    if checked_mode is not None and checked_mode & 0o077:
        blockers.append("private_key_permissions_too_open")
    has_private = any(marker in serialized_value for marker in _PRIVATE_MARKERS)
    has_public = any(marker in serialized_value for marker in _PUBLIC_MARKERS)
    if has_private:
        blockers.append("raw_private_key_material_serialized")
    if has_public:
        blockers.append("raw_public_key_material_serialized")
    if private_key_path_public:
        blockers.append("private_key_path_public")
    return LambdaSSHPrivateKeyFilePolicyReport(
        private_key_file_policy_status="policy_defined" if not blockers else "blocked",
        raw_key_material_serialized=has_private,
        public_key_material_serialized=has_public,
        private_key_path_public=private_key_path_public,
        blockers=sorted(set(blockers)),
        warnings=[
            "M055B does not read credentials; future live run must check mode safely",
            "private key file permissions must be 0600 or stricter",
        ],
    )


def load_lambda_ssh_private_key_file_policy(
    path: str | Path,
) -> LambdaSSHPrivateKeyFilePolicyReport:
    return LambdaSSHPrivateKeyFilePolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_private_key_file_policy(
    path: str | Path,
    report: LambdaSSHPrivateKeyFilePolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
