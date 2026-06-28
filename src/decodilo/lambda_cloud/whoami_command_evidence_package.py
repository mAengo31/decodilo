"""Immutable evidence package for M061 whoami identity command closeout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.whoami_command_reconciliation import (
    load_lambda_whoami_command_reconciliation,
)
from decodilo.lambda_cloud.whoami_command_success_record import (
    load_lambda_whoami_command_success_record,
)


class LambdaWhoamiCommandEvidenceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str


class LambdaWhoamiCommandEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    evidence_complete: bool
    whoami_command_success: bool
    evidence_refs: dict[str, LambdaWhoamiCommandEvidenceRef] = Field(default_factory=dict)
    missing_items: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaWhoamiCommandEvidencePackage:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M062 evidence package cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_whoami_command_evidence_package_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    expected_hashes: dict[str, str] | None = None,
) -> LambdaWhoamiCommandEvidencePackage:
    success = load_lambda_whoami_command_success_record(success_record)
    reconcile = load_lambda_whoami_command_reconciliation(reconciliation)
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
    refs: dict[str, LambdaWhoamiCommandEvidenceRef] = {}
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
    if success.status != "whoami_command_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    whoami_success = (
        success.status == "whoami_command_success"
        and reconcile.reconciliation_passed
        and not blockers
    )
    return LambdaWhoamiCommandEvidencePackage(
        evidence_complete=not blockers,
        whoami_command_success=whoami_success,
        evidence_refs=refs,
        missing_items=missing,
        hash_mismatches=mismatches,
        blockers=sorted(set(blockers)),
        warnings=[
            "M062 evidence package is offline and immutable-reference oriented",
            "M061 historical billable action is recorded but M062 performs none",
        ],
    )


def _ref(path: Path) -> LambdaWhoamiCommandEvidenceRef:
    return LambdaWhoamiCommandEvidenceRef(
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def load_lambda_whoami_command_evidence_package(
    path: str | Path,
) -> LambdaWhoamiCommandEvidencePackage:
    return LambdaWhoamiCommandEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_whoami_command_evidence_package(
    path: str | Path,
    report: LambdaWhoamiCommandEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
