"""Immutable evidence package for M063 GPU visibility closeout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.gpu_visibility_parsed_output_audit import (
    load_lambda_gpu_visibility_parsed_output_audit,
)
from decodilo.lambda_cloud.gpu_visibility_reconciliation import (
    load_lambda_gpu_visibility_reconciliation,
)
from decodilo.lambda_cloud.gpu_visibility_success_record import (
    load_lambda_gpu_visibility_success_record,
)


class LambdaGPUVisibilityEvidenceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str


class LambdaGPUVisibilityEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    evidence_complete: bool
    gpu_visibility_command_success: bool
    parsed_output_status: str
    evidence_refs: dict[str, LambdaGPUVisibilityEvidenceRef] = Field(default_factory=dict)
    missing_items: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaGPUVisibilityEvidencePackage:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M064 evidence package cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_gpu_visibility_evidence_package_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    parsed_output_audit: str | Path,
    expected_hashes: dict[str, str] | None = None,
) -> LambdaGPUVisibilityEvidencePackage:
    success = load_lambda_gpu_visibility_success_record(success_record)
    reconcile = load_lambda_gpu_visibility_reconciliation(reconciliation)
    audit = load_lambda_gpu_visibility_parsed_output_audit(parsed_output_audit)
    workdir = Path(success.source_workdir)
    required = {
        "success_record": Path(success_record),
        "parsed_output_audit": Path(parsed_output_audit),
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
    refs: dict[str, LambdaGPUVisibilityEvidenceRef] = {}
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
    blockers = [*success.blockers, *reconcile.errors, *audit.blockers]
    blockers.extend(f"missing_evidence:{item}" for item in missing)
    blockers.extend(f"hash_mismatch:{item}" for item in mismatches)
    if success.status not in {
        "gpu_visibility_query_success",
        "gpu_visibility_query_executed_output_hash_only",
    }:
        blockers.append("success_record_not_success_or_hash_only")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    if audit.parsed_output_audit_status == "missing_output":
        blockers.append("gpu_visibility_output_missing")
    gpu_success = (
        success.status
        in {"gpu_visibility_query_success", "gpu_visibility_query_executed_output_hash_only"}
        and reconcile.reconciliation_passed
        and audit.parsed_output_audit_status != "missing_output"
        and not blockers
    )
    warnings = [
        "M064 evidence package is offline and immutable-reference oriented",
        "M063 historical billable action is recorded but M064 performs none",
    ]
    if audit.parsed_output_audit_status == "output_hash_only":
        warnings.append("parsed GPU fields absent; evidence is hash-only")
    return LambdaGPUVisibilityEvidencePackage(
        evidence_complete=not blockers,
        gpu_visibility_command_success=gpu_success,
        parsed_output_status=audit.parsed_output_audit_status,
        evidence_refs=refs,
        missing_items=missing,
        hash_mismatches=mismatches,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def _ref(path: Path) -> LambdaGPUVisibilityEvidenceRef:
    return LambdaGPUVisibilityEvidenceRef(
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def load_lambda_gpu_visibility_evidence_package(
    path: str | Path,
) -> LambdaGPUVisibilityEvidencePackage:
    return LambdaGPUVisibilityEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_gpu_visibility_evidence_package(
    path: str | Path,
    report: LambdaGPUVisibilityEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
