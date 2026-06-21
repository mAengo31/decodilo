"""Encryption policy model for future remote artifact backends."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.remote_backend_credentials_model import SecretRef


class EncryptionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_schema_version: int = 1
    encryption_in_transit_required: bool = True
    encryption_at_rest_required: bool = True
    client_side_encryption_required: bool = False
    server_side_encryption_required: bool = True
    key_management_model: Literal[
        "not_configured",
        "provider_managed",
        "customer_managed",
        "client_side",
    ] = "provider_managed"
    key_ref: SecretRef | None = None


class EncryptionPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    policy: EncryptionPolicy

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_encryption_policy(policy: EncryptionPolicy) -> EncryptionPolicyReport:
    errors: list[str] = []
    warnings: list[str] = []
    if policy.encryption_in_transit_required is False:
        errors.append("encryption in transit is required for remote artifact backends")
    if policy.encryption_at_rest_required is False:
        errors.append("encryption at rest is required for remote artifact backends")
    if policy.server_side_encryption_required and policy.key_management_model == "not_configured":
        errors.append("server-side encryption requires a configured key-management model")
    if policy.client_side_encryption_required and policy.key_management_model != "client_side":
        errors.append("client-side encryption requires key_management_model=client_side")
    if (
        policy.key_management_model in {"customer_managed", "client_side"}
        and policy.key_ref is None
    ):
        warnings.append("customer/client-side key model needs a symbolic key_ref before review")
    return EncryptionPolicyReport(
        passed=not errors,
        errors=errors,
        warnings=warnings,
        policy=policy,
    )


def load_encryption_policy(path: str | Path) -> EncryptionPolicy:
    return EncryptionPolicy.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_encryption_policy_report(path: str | Path, report: EncryptionPolicyReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
