"""Immutable evidence package for M059 hostname identity command closeout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_hostname_identity_reconciliation import (
    load_lambda_ssh_hostname_identity_reconciliation,
)
from decodilo.lambda_cloud.ssh_hostname_identity_success_record import (
    load_lambda_ssh_hostname_identity_success_record,
)


class LambdaSSHHostnameIdentityEvidenceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str


class LambdaSSHHostnameIdentityEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    evidence_complete: bool
    ssh_hostname_identity_success: bool
    evidence_refs: dict[str, LambdaSSHHostnameIdentityEvidenceRef] = Field(
        default_factory=dict
    )
    missing_items: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaSSHHostnameIdentityEvidencePackage:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M060 evidence package cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_hostname_identity_evidence_package_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    expected_hashes: dict[str, str] | None = None,
) -> LambdaSSHHostnameIdentityEvidencePackage:
    success = load_lambda_ssh_hostname_identity_success_record(success_record)
    reconcile = load_lambda_ssh_hostname_identity_reconciliation(reconciliation)
    workdir = Path(success.source_workdir)
    required = {
        "success_record": Path(success_record),
        "run_report": workdir / "report.json",
        "journal": workdir / "journal.jsonl",
        "ledger": workdir / "ledger.json",
        "spend_audit": workdir / "spend-audit.json",
        "ssh_diagnostic": workdir / "ssh-connectivity-evidence.json",
        "ssh_host_discovery": workdir / "ssh-host-discovery.json",
        "transport_diagnostics": workdir / "transport-diagnostics.json",
        "final_discovery": Path(success.final_discovery_path),
        "reconciliation": Path(reconciliation),
    }
    refs: dict[str, LambdaSSHHostnameIdentityEvidenceRef] = {}
    missing: list[str] = []
    mismatches: list[str] = []
    for name, path in required.items():
        if not path.exists():
            missing.append(name)
            continue
        ref = _ref(path)
        refs[name] = ref
        if expected_hashes is not None and expected_hashes.get(name) != ref.sha256:
            mismatches.append(name)
    blockers = [*success.blockers, *reconcile.errors]
    blockers.extend(f"missing_evidence:{item}" for item in missing)
    blockers.extend(f"hash_mismatch:{item}" for item in mismatches)
    if success.status != "ssh_hostname_identity_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    ssh_success = (
        success.status == "ssh_hostname_identity_success"
        and reconcile.reconciliation_passed
        and not blockers
    )
    return LambdaSSHHostnameIdentityEvidencePackage(
        evidence_complete=not blockers,
        ssh_hostname_identity_success=ssh_success,
        evidence_refs=refs,
        missing_items=missing,
        hash_mismatches=mismatches,
        blockers=sorted(set(blockers)),
        warnings=[
            "M060 evidence package is offline and immutable-reference oriented",
            "M059 historical billable action is recorded but M060 performs none",
        ],
    )


def _ref(path: Path) -> LambdaSSHHostnameIdentityEvidenceRef:
    return LambdaSSHHostnameIdentityEvidenceRef(
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def load_lambda_ssh_hostname_identity_evidence_package(
    path: str | Path,
) -> LambdaSSHHostnameIdentityEvidencePackage:
    return LambdaSSHHostnameIdentityEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_hostname_identity_evidence_package(
    path: str | Path,
    report: LambdaSSHHostnameIdentityEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
