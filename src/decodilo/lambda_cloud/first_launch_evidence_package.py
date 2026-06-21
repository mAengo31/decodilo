"""Evidence package for future real Lambda first-launch design review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaFirstLaunchEvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    ref: str
    required: bool = True
    present: bool = False
    sha256: str | None = None


class LambdaFirstLaunchEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    package_id: str = "lambda-first-launch-evidence-package-m023"
    evidence_items: list[LambdaFirstLaunchEvidenceItem]
    evidence_complete: bool
    missing_items: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    future_real_launch_review_candidate: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFirstLaunchEvidencePackage:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M023 evidence package cannot enable mutation or launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_first_launch_evidence_package(
    *,
    m019c_discovery: str | Path | None = None,
    m019c_audit: str | Path | None = None,
    m019c_preflight: str | Path | None = None,
    m020_report: str | Path | None = None,
    m021_fake_lifecycle_report: str | Path | None = None,
    m022_stress_report: str | Path | None = None,
    m022_teardown_audit: str | Path | None = None,
    m022_real_mutation_absence_audit: str | Path | None = None,
    m022_readiness_package: str | Path | None = None,
    proposal: str | Path | None = None,
    operation_spec: str | Path | None = None,
    arming_gate: str | Path | None = None,
    kill_switch: str | Path | None = None,
    termination_policy: str | Path | None = None,
    safety_case: str | Path | None = None,
    failure_modes: str | Path | None = None,
    expected_hashes: dict[str, str] | None = None,
) -> LambdaFirstLaunchEvidencePackage:
    refs = {
        "m019c_discovery": m019c_discovery,
        "m019c_audit": m019c_audit,
        "m019c_preflight": m019c_preflight,
        "m020_report": m020_report,
        "m021_fake_lifecycle_report": m021_fake_lifecycle_report,
        "m022_stress_report": m022_stress_report,
        "m022_teardown_audit": m022_teardown_audit,
        "m022_real_mutation_absence_audit": m022_real_mutation_absence_audit,
        "m022_readiness_package": m022_readiness_package,
        "m023_mutation_boundary_proposal": proposal,
        "m023_operation_spec": operation_spec,
        "m023_arming_gate_design": arming_gate,
        "m023_kill_switch_design": kill_switch,
        "m023_termination_verification_policy": termination_policy,
        "m023_first_launch_safety_case": safety_case,
        "m023_failure_mode_table": failure_modes,
    }
    items: list[LambdaFirstLaunchEvidenceItem] = []
    missing: list[str] = []
    mismatches: list[str] = []
    for item_id, value in refs.items():
        path = Path(value) if value is not None else None
        if path is None or not path.exists():
            missing.append(item_id)
            items.append(
                LambdaFirstLaunchEvidenceItem(
                    item_id=item_id,
                    ref="" if path is None else str(path),
                )
            )
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = None if expected_hashes is None else expected_hashes.get(item_id)
        if expected is not None and expected != digest:
            mismatches.append(item_id)
        items.append(
            LambdaFirstLaunchEvidenceItem(
                item_id=item_id,
                ref=str(path),
                present=True,
                sha256=digest,
            )
        )
    blockers = [f"missing evidence: {item}" for item in missing]
    blockers.extend(f"hash mismatch: {item}" for item in mismatches)
    complete = not blockers
    return LambdaFirstLaunchEvidencePackage(
        evidence_items=items,
        evidence_complete=complete,
        missing_items=missing,
        hash_mismatches=mismatches,
        blockers=blockers,
        warnings=[
            "Evidence package is for design review only; it cannot approve launch.",
        ],
        future_real_launch_review_candidate=complete,
    )


def load_lambda_first_launch_evidence_package(
    path: str | Path,
) -> LambdaFirstLaunchEvidencePackage:
    return LambdaFirstLaunchEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_first_launch_evidence_package(
    path: str | Path,
    package: LambdaFirstLaunchEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.to_json(), encoding="utf-8")
