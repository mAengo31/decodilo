"""Evidence package for the completed Lambda lifecycle smoke."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lifecycle_smoke_postrun_reconciliation import (
    load_lambda_lifecycle_smoke_postrun_reconciliation,
)
from decodilo.lambda_cloud.lifecycle_smoke_success_record import (
    load_lambda_lifecycle_smoke_success_record,
)


class LambdaLifecycleSmokeEvidenceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str


class LambdaLifecycleSmokeEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    evidence_complete: bool
    lifecycle_smoke_success: bool
    evidence_refs: dict[str, LambdaLifecycleSmokeEvidenceRef] = Field(default_factory=dict)
    missing_items: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_read_only(self) -> LambdaLifecycleSmokeEvidencePackage:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("evidence package cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lifecycle_smoke_evidence_package_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
) -> LambdaLifecycleSmokeEvidencePackage:
    success = load_lambda_lifecycle_smoke_success_record(success_record)
    reconcile = load_lambda_lifecycle_smoke_postrun_reconciliation(reconciliation)
    workdir = Path(success.source_workdir)
    required = {
        "success_record": Path(success_record),
        "reconciliation": Path(reconciliation),
        "launch_report": workdir / "report.json",
        "journal": workdir / "journal.jsonl",
        "ledger": workdir / "ledger.json",
        "spend_audit": workdir / "spend-audit.json",
    }
    refs: dict[str, LambdaLifecycleSmokeEvidenceRef] = {}
    missing: list[str] = []
    for name, path in required.items():
        if path.exists():
            refs[name] = _ref(path)
        else:
            missing.append(name)
    blockers = [*success.blockers, *reconcile.errors]
    blockers.extend(f"missing_evidence:{item}" for item in missing)
    lifecycle_success = (
        success.status == "lifecycle_smoke_success"
        and reconcile.reconciliation_passed
        and not blockers
    )
    return LambdaLifecycleSmokeEvidencePackage(
        evidence_complete=not blockers,
        lifecycle_smoke_success=lifecycle_success,
        evidence_refs=refs,
        missing_items=missing,
        hash_mismatches=[],
        blockers=sorted(set(blockers)),
        warnings=[
            "evidence package is immutable-reference oriented",
            "M047 performs no new Lambda mutation",
        ],
    )


def _ref(path: Path) -> LambdaLifecycleSmokeEvidenceRef:
    return LambdaLifecycleSmokeEvidenceRef(
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def load_lambda_lifecycle_smoke_evidence_package(
    path: str | Path,
) -> LambdaLifecycleSmokeEvidencePackage:
    return LambdaLifecycleSmokeEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lifecycle_smoke_evidence_package(
    path: str | Path,
    report: LambdaLifecycleSmokeEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
