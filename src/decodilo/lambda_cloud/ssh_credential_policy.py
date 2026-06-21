"""SSH credential/source policy for future Lambda connectivity planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHCredentialPolicyStatus = Literal["policy_defined", "blocked"]

_SECRET_MARKERS = (
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "BEGIN EC PRIVATE KEY",
    "PRIVATE KEY-----",
    "ssh-rsa ",
    "ssh-ed25519 ",
    "ecdsa-sha2-",
)


class LambdaSSHCredentialPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    credential_policy_status: LambdaSSHCredentialPolicyStatus
    existing_key_required: bool = True
    selected_ssh_key_hash: str | None = None
    key_creation_allowed: bool = False
    key_deletion_allowed: bool = False
    private_key_material_serialized: bool = False
    raw_public_key_material_serialized: bool = False
    private_key_access_approved_in_m053: bool = False
    future_m054_key_source_required: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_credentials(self) -> LambdaSSHCredentialPolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.key_creation_allowed
            or self.key_deletion_allowed
            or self.private_key_material_serialized
            or self.raw_public_key_material_serialized
            or self.private_key_access_approved_in_m053
        ):
            raise ValueError(
                "M053 credential policy cannot expose secrets or enable key operations"
            )
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSSHCredentialPolicy = LambdaSSHCredentialPolicyReport


def build_lambda_ssh_credential_policy_from_path(
    ssh_key_selection: str | Path,
) -> LambdaSSHCredentialPolicyReport:
    path = Path(ssh_key_selection)
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(payload, sort_keys=True)
    blockers: list[str] = []
    selected_hash = payload.get("selected_ssh_key_name_redacted_or_hash")
    if payload.get("create_key_requested"):
        blockers.append("ssh_key_creation_requested")
    if payload.get("delete_key_requested"):
        blockers.append("ssh_key_deletion_requested")
    if payload.get("raw_public_key_material_present"):
        blockers.append("raw_public_key_material_present")
    if not payload.get("selection_passed"):
        blockers.append("ssh_key_selection_not_passed")
    if not selected_hash:
        blockers.append("selected_ssh_key_hash_missing")
    if any(marker in serialized for marker in _SECRET_MARKERS):
        blockers.append("secret_or_key_material_serialized")
    return LambdaSSHCredentialPolicyReport(
        credential_policy_status="policy_defined" if not blockers else "blocked",
        selected_ssh_key_hash=selected_hash,
        private_key_material_serialized=any(
            "PRIVATE KEY" in line for line in serialized.splitlines()
        ),
        raw_public_key_material_serialized=bool(payload.get("raw_public_key_material_present")),
        blockers=sorted(set(blockers)),
        warnings=[
            "existing SSH key may be referenced by hash/redaction only in public M053 reports",
            "M053 does not approve private key access or SSH execution",
            "future M054B must use a separate private-key reference policy "
            "without serializing key material",
        ],
    )


def load_lambda_ssh_credential_policy(path: str | Path) -> LambdaSSHCredentialPolicyReport:
    return LambdaSSHCredentialPolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_credential_policy(
    path: str | Path,
    report: LambdaSSHCredentialPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
