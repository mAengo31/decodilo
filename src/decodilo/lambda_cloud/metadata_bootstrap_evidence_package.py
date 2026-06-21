"""Immutable evidence package for M051B metadata-only Lambda bootstrap closeout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.metadata_bootstrap_reconciliation import (
    load_lambda_metadata_bootstrap_reconciliation,
)
from decodilo.lambda_cloud.metadata_bootstrap_success_record import (
    load_lambda_metadata_bootstrap_success_record,
)


class LambdaMetadataBootstrapEvidenceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str


class LambdaMetadataBootstrapEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    evidence_complete: bool
    metadata_bootstrap_success: bool
    evidence_refs: dict[str, LambdaMetadataBootstrapEvidenceRef] = Field(
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
    def _validate_closeout_only(self) -> LambdaMetadataBootstrapEvidencePackage:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M052 evidence package cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_metadata_bootstrap_evidence_package_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    expected_hashes: dict[str, str] | None = None,
    metadata_plan: str | Path = "/tmp/decodilo-lambda-m051-metadata-bootstrap-plan.json",
    execution_gate: str | Path = "/tmp/decodilo-lambda-m051-bootstrap-execution-gate-check.json",
    no_mutation_no_ssh_audit: str | Path = (
        "/tmp/decodilo-lambda-m051-no-mutation-no-ssh-audit.json"
    ),
    reviewer_bridge: str | Path = "/tmp/decodilo-lambda-m051-reviewer-bridge.json",
    arming_gate: str | Path = "/tmp/decodilo-lambda-m051-arming-gate-check.json",
    m050_report: str | Path = "/tmp/decodilo-lambda-m050-report.json",
) -> LambdaMetadataBootstrapEvidencePackage:
    success = load_lambda_metadata_bootstrap_success_record(success_record)
    reconcile = load_lambda_metadata_bootstrap_reconciliation(reconciliation)
    workdir = Path(success.source_workdir)
    required = {
        "success_record": Path(success_record),
        "launch_report": workdir / "report.json",
        "journal": workdir / "journal.jsonl",
        "ledger": workdir / "ledger.json",
        "spend_audit": workdir / "spend-audit.json",
        "post_discovery": Path(success.post_discovery_path),
        "reconciliation": Path(reconciliation),
        "metadata_plan": Path(metadata_plan),
        "execution_gate": Path(execution_gate),
        "no_mutation_no_ssh_audit": Path(no_mutation_no_ssh_audit),
        "reviewer_bridge": Path(reviewer_bridge),
        "arming_gate": Path(arming_gate),
        "m050_report": Path(m050_report),
    }
    refs: dict[str, LambdaMetadataBootstrapEvidenceRef] = {}
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
    if success.status != "metadata_bootstrap_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    if success.ssh_attempted:
        blockers.append("ssh_attempted")
    if success.remote_command_attempted:
        blockers.append("remote_command_attempted")
    if success.package_install_attempted:
        blockers.append("package_install_attempted")
    if success.training_attempted:
        blockers.append("training_attempted")
    metadata_success = (
        success.status == "metadata_bootstrap_success"
        and reconcile.reconciliation_passed
        and not blockers
    )
    return LambdaMetadataBootstrapEvidencePackage(
        evidence_complete=not blockers,
        metadata_bootstrap_success=metadata_success,
        evidence_refs=refs,
        missing_items=missing,
        hash_mismatches=mismatches,
        blockers=sorted(set(blockers)),
        warnings=[
            "M052 evidence package is offline and immutable-reference oriented",
            "M051B historical billable action is recorded but M052 performs none",
        ],
    )


def _ref(path: Path) -> LambdaMetadataBootstrapEvidenceRef:
    return LambdaMetadataBootstrapEvidenceRef(
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def load_lambda_metadata_bootstrap_evidence_package(
    path: str | Path,
) -> LambdaMetadataBootstrapEvidencePackage:
    return LambdaMetadataBootstrapEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_metadata_bootstrap_evidence_package(
    path: str | Path,
    report: LambdaMetadataBootstrapEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
