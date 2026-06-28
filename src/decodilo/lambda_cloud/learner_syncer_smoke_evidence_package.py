"""M079R2 learner/syncer smoke evidence package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.learner_syncer_smoke_reconciliation import (
    load_lambda_learner_syncer_smoke_reconciliation,
)
from decodilo.lambda_cloud.learner_syncer_smoke_success_record import (
    load_lambda_learner_syncer_smoke_success_record,
)


class LambdaLearnerSyncerSmokeEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M080"
    evidence_complete: bool
    learner_syncer_smoke_success: bool
    reconciliation_passed: bool
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    missing_items: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_package(self) -> LambdaLearnerSyncerSmokeEvidencePackage:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M080 evidence package must remain offline and disabled")
        if self.evidence_complete and (self.blockers or self.missing_items):
            raise ValueError("complete evidence package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_learner_syncer_smoke_evidence_package_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
) -> LambdaLearnerSyncerSmokeEvidencePackage:
    record = load_lambda_learner_syncer_smoke_success_record(success_record)
    reconcile = load_lambda_learner_syncer_smoke_reconciliation(reconciliation)
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
    if record.success_status != "remote_learner_syncer_smoke_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    if hash_mismatches:
        blockers.append("artifact_hash_mismatch")
    evidence_complete = not blockers and not missing_items
    return LambdaLearnerSyncerSmokeEvidencePackage(
        evidence_complete=evidence_complete,
        learner_syncer_smoke_success=(
            record.success_status == "remote_learner_syncer_smoke_success"
        ),
        reconciliation_passed=reconcile.reconciliation_passed,
        artifact_hashes=artifact_hashes,
        missing_items=missing_items,
        hash_mismatches=hash_mismatches,
        blockers=blockers,
        warnings=["evidence package is local-only and performs no Lambda calls"],
    )


def load_lambda_learner_syncer_smoke_evidence_package(
    path: str | Path,
) -> LambdaLearnerSyncerSmokeEvidencePackage:
    return LambdaLearnerSyncerSmokeEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_learner_syncer_smoke_evidence_package(
    path: str | Path,
    report: LambdaLearnerSyncerSmokeEvidencePackage,
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
