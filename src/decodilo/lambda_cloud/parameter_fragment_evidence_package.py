"""M087R parameter-fragment smoke evidence package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.parameter_fragment_reconciliation import (
    load_lambda_parameter_fragment_reconciliation,
)
from decodilo.lambda_cloud.parameter_fragment_success_record import (
    load_lambda_parameter_fragment_success_record,
)


class LambdaParameterFragmentEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M088"
    evidence_complete: bool
    parameter_fragment_success: bool
    reconciliation_passed: bool
    fragment_semantics_confirmed: bool
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    missing_items: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_package(self) -> LambdaParameterFragmentEvidencePackage:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M088 evidence package must remain offline and disabled")
        if self.evidence_complete and (self.blockers or self.missing_items):
            raise ValueError("complete evidence package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_parameter_fragment_evidence_package_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
) -> LambdaParameterFragmentEvidencePackage:
    record = load_lambda_parameter_fragment_success_record(success_record)
    reconcile = load_lambda_parameter_fragment_reconciliation(reconciliation)
    artifact_hashes = {
        "success_record": _sha256_file(Path(success_record)),
        "reconciliation": _sha256_file(Path(reconciliation)),
    }
    missing_items: list[str] = []
    hash_mismatches: list[str] = []
    for name, path_text in record.artifact_paths.items():
        path = Path(path_text)
        if not path.exists():
            missing_items.append(name)
            continue
        digest = _sha256_file(path)
        artifact_hashes[name] = digest
        expected = record.artifact_hashes.get(name)
        if expected and expected != digest:
            hash_mismatches.append(name)
    blockers: list[str] = []
    if record.success_status != "remote_parameter_fragment_smoke_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    if not reconcile.fragment_semantics_confirmed:
        blockers.append("fragment_semantics_not_confirmed")
    if hash_mismatches:
        blockers.append("artifact_hash_mismatch")
    evidence_complete = not blockers and not missing_items
    return LambdaParameterFragmentEvidencePackage(
        evidence_complete=evidence_complete,
        parameter_fragment_success=(
            record.success_status == "remote_parameter_fragment_smoke_success"
        ),
        reconciliation_passed=reconcile.reconciliation_passed,
        fragment_semantics_confirmed=reconcile.fragment_semantics_confirmed,
        artifact_hashes=artifact_hashes,
        missing_items=missing_items,
        hash_mismatches=hash_mismatches,
        blockers=blockers,
        warnings=["evidence package is local-only and performs no Lambda calls"],
    )


def load_lambda_parameter_fragment_evidence_package(
    path: str | Path,
) -> LambdaParameterFragmentEvidencePackage:
    return LambdaParameterFragmentEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_parameter_fragment_evidence_package(
    path: str | Path,
    report: LambdaParameterFragmentEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
