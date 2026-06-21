"""Evidence package for fake Lambda launch lifecycle readiness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_lifecycle_stress import FakeLambdaLifecycleStressReport
from decodilo.lambda_cloud.fake_teardown_audit import FakeLambdaTeardownAuditReport
from decodilo.lambda_cloud.real_mutation_absence_audit import (
    audit_real_lambda_mutation_absence,
)


class FakeLambdaLaunchReadinessPackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    m020_report_ref: str
    approval_manifest_ref: str
    preflight_report_ref: str
    stress_report_ref: str
    teardown_audit_ref: str
    real_mutation_absence_audit_ref: str | None = None
    evidence_hashes: dict[str, str] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    future_real_launch_candidate: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_fake_lambda_launch_readiness_package(
    *,
    m020_report: str | Path,
    approval_manifest: str | Path,
    preflight_report: str | Path,
    stress_report: str | Path,
    teardown_audit: str | Path,
    project_root: str | Path = ".",
) -> FakeLambdaLaunchReadinessPackage:
    refs = {
        "m020_report": Path(m020_report),
        "approval_manifest": Path(approval_manifest),
        "preflight_report": Path(preflight_report),
        "stress_report": Path(stress_report),
        "teardown_audit": Path(teardown_audit),
    }
    blockers: list[str] = []
    warnings: list[str] = []
    hashes: dict[str, str] = {}
    for name, path in refs.items():
        if not path.exists():
            blockers.append(f"missing evidence: {name}")
            continue
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if refs["stress_report"].exists():
        stress = FakeLambdaLifecycleStressReport.model_validate_json(
            refs["stress_report"].read_text(encoding="utf-8")
        )
        if not stress.mutation_contract_passed:
            blockers.append("fake mutation contract did not pass stress")
        if stress.manual_review_required:
            warnings.append("stress report requires manual review")
    if refs["teardown_audit"].exists():
        audit = FakeLambdaTeardownAuditReport.model_validate_json(
            refs["teardown_audit"].read_text(encoding="utf-8")
        )
        if not audit.passed:
            blockers.append("teardown audit failed")
    absence = audit_real_lambda_mutation_absence(project_root)
    if not absence.passed:
        blockers.append("real mutation absence audit failed")
    return FakeLambdaLaunchReadinessPackage(
        m020_report_ref=str(m020_report),
        approval_manifest_ref=str(approval_manifest),
        preflight_report_ref=str(preflight_report),
        stress_report_ref=str(stress_report),
        teardown_audit_ref=str(teardown_audit),
        evidence_hashes=hashes,
        blockers=blockers,
        warnings=warnings,
    )


def write_fake_lambda_launch_readiness_package(
    path: str | Path,
    package: FakeLambdaLaunchReadinessPackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.to_json(), encoding="utf-8")
