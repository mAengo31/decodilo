"""Read-only existing SSH key selection for Strand-compatible launch plans."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)

LambdaSSHKeySelectionSource = Literal["read_only_discovery", "operator_selected"]


class LambdaExistingSSHKeySelectionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    discovered_ssh_key_count: int
    selected_ssh_key_name_redacted_or_hash: str | None = None
    selected_ssh_key_name_for_payload: str | None = None
    key_source: LambdaSSHKeySelectionSource | None = None
    selection_passed: bool
    create_key_requested: bool = False
    delete_key_requested: bool = False
    raw_public_key_material_present: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaExistingSSHKeySelectionReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.create_key_requested
            or self.delete_key_requested
        ):
            raise ValueError("SSH key selection cannot enable launch or mutate SSH keys")
        if self.raw_public_key_material_present:
            raise ValueError("SSH key selection cannot store raw public key material")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaExistingSSHKeySelection = LambdaExistingSSHKeySelectionReport


def select_existing_lambda_ssh_key(
    *,
    discovery: LambdaLiveDiscoveryReport,
    operator_selected_key_name: str | None = None,
) -> LambdaExistingSSHKeySelectionReport:
    discovered = [key.name for key in discovery.ssh_keys if key.name]
    discovered_set = set(discovered)
    warnings = ["SSH key selection is read-only and cannot create or delete keys"]
    errors: list[str] = []
    selected: str | None = None
    source: LambdaSSHKeySelectionSource | None = None
    if operator_selected_key_name:
        source = "operator_selected"
        selected = operator_selected_key_name
        if discovered_set and selected not in discovered_set:
            errors.append("operator selected SSH key was not found in read-only discovery")
    elif discovered:
        source = "read_only_discovery"
        selected = sorted(discovered)[0]
    else:
        errors.append("no existing SSH key names discovered or selected")
    return LambdaExistingSSHKeySelectionReport(
        discovered_ssh_key_count=len(discovered),
        selected_ssh_key_name_redacted_or_hash=(
            None if selected is None else _hash_key_name(selected)
        ),
        selected_ssh_key_name_for_payload=selected,
        key_source=source,
        selection_passed=not errors,
        warnings=warnings,
        errors=errors,
    )


def select_existing_lambda_ssh_key_from_path(
    *,
    discovery_report: str | Path,
    operator_selected_key_name: str | None = None,
) -> LambdaExistingSSHKeySelectionReport:
    return select_existing_lambda_ssh_key(
        discovery=load_lambda_live_discovery_report(discovery_report),
        operator_selected_key_name=operator_selected_key_name,
    )


def _hash_key_name(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def load_lambda_existing_ssh_key_selection(
    path: str | Path,
) -> LambdaExistingSSHKeySelectionReport:
    return LambdaExistingSSHKeySelectionReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_existing_ssh_key_selection(
    path: str | Path,
    report: LambdaExistingSSHKeySelectionReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
