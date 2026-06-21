"""Private key reference policy for future SSH connectivity probes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHPrivateKeyReferencePolicyStatus = Literal["policy_defined", "blocked"]

_SECRET_MARKERS = (
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "BEGIN EC PRIVATE KEY",
    "PRIVATE KEY-----",
    "ssh-rsa ",
    "ssh-ed25519 ",
    "ecdsa-sha2-",
)


class LambdaSSHPrivateKeyReferencePolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    key_reference_policy_status: LambdaSSHPrivateKeyReferencePolicyStatus
    selected_ssh_key_hash: str | None = None
    future_private_key_reference_required: bool = True
    private_key_material_serialized: bool = False
    public_key_material_serialized: bool = False
    credential_used_in_m054a: bool = False
    private_key_existence_checked_in_m054a: bool = False
    raw_key_name_public: bool = False
    public_report_key_reference: str = "<redacted-private-key-reference>"
    future_allowed_reference_types: list[str] = Field(
        default_factory=lambda: ["operator_provided_path", "approved_default_key_lookup"]
    )
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_reference_policy(self) -> LambdaSSHPrivateKeyReferencePolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.private_key_material_serialized
            or self.public_key_material_serialized
            or self.credential_used_in_m054a
            or self.private_key_existence_checked_in_m054a
            or self.raw_key_name_public
        ):
            raise ValueError("M054A cannot expose or use SSH key material")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSSHPrivateKeyReferencePolicy = LambdaSSHPrivateKeyReferencePolicyReport


def build_lambda_ssh_private_key_reference_policy_from_path(
    ssh_key_selection: str | Path,
) -> LambdaSSHPrivateKeyReferencePolicyReport:
    payload: dict[str, Any] = json.loads(Path(ssh_key_selection).read_text(encoding="utf-8"))
    serialized = json.dumps(payload, sort_keys=True)
    blockers: list[str] = []
    selected_hash = payload.get("selected_ssh_key_name_redacted_or_hash")
    if not payload.get("selection_passed"):
        blockers.append("ssh_key_selection_not_passed")
    if not selected_hash:
        blockers.append("selected_ssh_key_hash_missing")
    if any(marker in serialized for marker in _SECRET_MARKERS):
        blockers.append("ssh_key_material_serialized")
    if payload.get("raw_public_key_material_present"):
        blockers.append("raw_public_key_material_present")
    if payload.get("create_key_requested") or payload.get("delete_key_requested"):
        blockers.append("ssh_key_create_delete_requested")
    return LambdaSSHPrivateKeyReferencePolicyReport(
        key_reference_policy_status="policy_defined" if not blockers else "blocked",
        selected_ssh_key_hash=selected_hash,
        private_key_material_serialized="PRIVATE KEY" in serialized,
        public_key_material_serialized=bool(payload.get("raw_public_key_material_present")),
        blockers=sorted(set(blockers)),
        warnings=[
            "M054A does not read or validate a private key file",
            "future M054B must receive an explicit private key reference "
            "without serializing material",
            "public reports must keep private key references redacted",
        ],
    )


def load_lambda_ssh_private_key_reference_policy(
    path: str | Path,
) -> LambdaSSHPrivateKeyReferencePolicyReport:
    return LambdaSSHPrivateKeyReferencePolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_private_key_reference_policy(
    path: str | Path,
    report: LambdaSSHPrivateKeyReferencePolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
