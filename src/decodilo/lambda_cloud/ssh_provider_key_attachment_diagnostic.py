"""Offline provider-key attachment diagnostic for SSH connectivity failures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHProviderKeyAttachmentDiagnosticStatus = Literal[
    "evidence_consistent",
    "inconclusive",
    "mismatch",
]


class LambdaSSHProviderKeyAttachmentDiagnosticReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selected_key_hash: str | None = None
    local_private_key_matches_public_identity: bool | None = None
    provider_key_record_matched: bool | None = None
    provider_user_id_field_present: bool = False
    provider_user_id_field_missing_not_blocking: bool = True
    key_attachment_diagnostic_status: LambdaSSHProviderKeyAttachmentDiagnosticStatus
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaSSHProviderKeyAttachmentDiagnosticReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.provider_user_id_field_missing_not_blocking
        ):
            raise ValueError("provider key diagnostic cannot enable launch")
        if self.key_attachment_diagnostic_status != "mismatch" and self.blockers:
            raise ValueError("non-mismatch provider diagnostic cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_provider_key_attachment_diagnostic_from_paths(
    *,
    ssh_key_selection: str | Path,
    launch_report: str | Path | None = None,
    provider_key_list: str | Path | None = None,
    local_private_key_matches_public_identity: bool | None = None,
) -> LambdaSSHProviderKeyAttachmentDiagnosticReport:
    selection = _load_json(ssh_key_selection)
    selected_hash = selection.get("selected_ssh_key_name_redacted_or_hash")
    launch = _load_json(launch_report) if launch_report else {}
    provider = _load_json(provider_key_list) if provider_key_list else {}
    launch_hash = launch.get("selected_ssh_key_hash")
    provider_match = _provider_contains_key_hash(provider, selected_hash)
    user_id_present = _provider_user_id_present(provider, selected_hash)
    blockers: list[str] = []
    warnings: list[str] = []
    if not selected_hash:
        blockers.append("selected_key_hash_missing")
    if launch_hash and selected_hash and launch_hash != selected_hash:
        blockers.append("selected_launch_key_hash_mismatch")
    if local_private_key_matches_public_identity is False:
        blockers.append("local_private_key_public_identity_mismatch")
    if provider_match is None:
        warnings.append("provider key list unavailable or did not include public key records")
    elif not provider_match:
        blockers.append("provider_key_record_not_matched")
    if not user_id_present:
        warnings.append("provider user_id field missing; this is not a blocker by itself")
    if blockers:
        status: LambdaSSHProviderKeyAttachmentDiagnosticStatus = "mismatch"
    elif provider_match is True or local_private_key_matches_public_identity is True:
        status = "evidence_consistent"
    else:
        status = "inconclusive"
    return LambdaSSHProviderKeyAttachmentDiagnosticReport(
        selected_key_hash=selected_hash,
        local_private_key_matches_public_identity=local_private_key_matches_public_identity,
        provider_key_record_matched=provider_match,
        provider_user_id_field_present=user_id_present,
        key_attachment_diagnostic_status=status,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    target = Path(path)
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def _provider_contains_key_hash(payload: Any, selected_hash: str | None) -> bool | None:
    if not selected_hash:
        return None
    found_key_like = False

    def walk(value: Any) -> bool:
        nonlocal found_key_like
        if isinstance(value, dict):
            if "key_id" in value or "public_key_fingerprint" in value or "fingerprint" in value:
                found_key_like = True
            if _matches_selected_hash(value.get("name"), selected_hash) or (
                value.get("selected_ssh_key_name_redacted_or_hash") == selected_hash
            ):
                return True
            return any(walk(child) for child in value.values())
        if isinstance(value, list):
            return any(walk(child) for child in value)
        return False

    matched = walk(payload)
    if matched:
        return True
    return False if found_key_like else None


def _provider_user_id_present(payload: Any, selected_hash: str | None) -> bool:
    def walk(value: Any) -> bool:
        if isinstance(value, dict):
            if (
                (selected_hash is None or _matches_selected_hash(value.get("name"), selected_hash))
                and value.get("user_id")
            ):
                return True
            return any(walk(child) for child in value.values())
        if isinstance(value, list):
            return any(walk(child) for child in value)
        return False

    return walk(payload)


def _matches_selected_hash(value: Any, selected_hash: str | None) -> bool:
    if value is None or selected_hash is None:
        return False
    text = str(value)
    return text == selected_hash or (
        selected_hash.startswith("sha256:")
        and selected_hash == f"sha256:{hashlib.sha256(text.encode()).hexdigest()[:16]}"
    )


def load_lambda_ssh_provider_key_attachment_diagnostic(
    path: str | Path,
) -> LambdaSSHProviderKeyAttachmentDiagnosticReport:
    return LambdaSSHProviderKeyAttachmentDiagnosticReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_provider_key_attachment_diagnostic(
    path: str | Path,
    report: LambdaSSHProviderKeyAttachmentDiagnosticReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
