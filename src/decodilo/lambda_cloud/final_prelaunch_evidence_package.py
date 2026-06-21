"""Final M025 pre-launch evidence package for future first-launch review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaFinalPrelaunchEvidenceStatus = Literal["complete", "incomplete", "blocked"]


class LambdaFinalPrelaunchEvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    ref: str = ""
    required: bool = True
    present: bool = False
    sha256: str | None = None


class LambdaFinalPrelaunchEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    package_schema_version: int = 1
    package_id: str = "lambda-final-prelaunch-evidence-m025"
    evidence_items: list[LambdaFinalPrelaunchEvidenceItem]
    missing_items: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    stale_items: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_complete: bool
    future_first_launch_candidate: bool = False
    evidence_status: LambdaFinalPrelaunchEvidenceStatus = "incomplete"
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFinalPrelaunchEvidencePackage:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M025 evidence package cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_final_prelaunch_evidence_package(
    *,
    expected_hashes: dict[str, str] | None = None,
    **refs: str | Path | None,
) -> LambdaFinalPrelaunchEvidencePackage:
    required = {
        "m019c_discovery",
        "m019c_audit",
        "m020_report",
        "m022_readiness_package",
        "m023_evidence_package",
        "m024_skeleton_audit",
    }
    optional = {
        "m019c_live_ledger",
        "m019c_live_preflight",
        "m021_fake_lifecycle_report",
        "m021_fake_teardown_verification",
        "m022_fake_lifecycle_stress",
        "m022_fake_teardown_audit",
        "m022_real_mutation_absence_audit",
        "m023_mutation_boundary_proposal",
        "m023_operation_spec",
        "m023_arming_gate_design",
        "m023_kill_switch_design",
        "m023_termination_verification_policy",
        "m023_first_launch_safety_case",
        "m023_failure_mode_table",
        "m023_review_record",
        "m024_budget_lock",
        "m024_idempotency_plan",
        "m024_resource_scope",
        "m024_prepare_launch_review_plan",
        "m024_disabled_launch_test_report",
        "m025_spend_safety_review",
        "m025_resource_ownership_review",
        "m025_secret_handling_review",
        "m025_semantic_mutation_audit",
        "m025_operator_checklist",
        "m025_termination_runbook",
        "m025_launch_runbook",
    }
    ids = sorted(required | optional)
    items: list[LambdaFinalPrelaunchEvidenceItem] = []
    missing: list[str] = []
    mismatches: list[str] = []
    for item_id in ids:
        value = refs.get(item_id)
        path = Path(value) if value is not None else None
        is_required = item_id in required
        if path is None or not path.exists():
            if is_required:
                missing.append(item_id)
            items.append(
                LambdaFinalPrelaunchEvidenceItem(
                    item_id=item_id,
                    ref="" if path is None else str(path),
                    required=is_required,
                )
            )
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = None if expected_hashes is None else expected_hashes.get(item_id)
        if expected is not None and expected != digest:
            mismatches.append(item_id)
        items.append(
            LambdaFinalPrelaunchEvidenceItem(
                item_id=item_id,
                ref=str(path),
                required=is_required,
                present=True,
                sha256=digest,
            )
        )
    blockers = [f"missing required evidence: {item}" for item in missing]
    blockers.extend(f"hash mismatch: {item}" for item in mismatches)
    complete = not blockers
    return LambdaFinalPrelaunchEvidencePackage(
        evidence_items=items,
        missing_items=missing,
        hash_mismatches=mismatches,
        blockers=blockers,
        warnings=["Final prelaunch package is review-only and cannot enable launch."],
        evidence_complete=complete,
        evidence_status="complete" if complete else "blocked",
        future_first_launch_candidate=complete,
    )


def load_lambda_final_prelaunch_evidence_package(
    path: str | Path,
) -> LambdaFinalPrelaunchEvidencePackage:
    return LambdaFinalPrelaunchEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_final_prelaunch_evidence_package(
    path: str | Path,
    package: LambdaFinalPrelaunchEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.to_json(), encoding="utf-8")
