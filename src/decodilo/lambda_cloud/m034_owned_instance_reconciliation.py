"""Owned-instance reconciliation for M034C launch failures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m034_discovery_diff import LambdaM034DiscoveryDiffReport
from decodilo.lambda_cloud.real_launch_journal import replay_m029_launch_journal
from decodilo.lambda_cloud.real_launch_result import redact_instance_id

LambdaM034OwnershipConfidence = Literal["exact", "high", "medium", "low", "none"]


class LambdaM034OwnedInstanceReconciliationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    owned_instance_id_found: bool
    owned_instance_id_redacted: str | None = None
    candidate_count: int = 0
    confidence: LambdaM034OwnershipConfidence = "none"
    terminate_allowed: bool = False
    terminate_allowed_reason: str
    manual_review_required: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM034OwnedInstanceReconciliationReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M034 owned-instance reconciliation cannot enable launch")
        if self.terminate_allowed and self.confidence not in {"exact", "high"}:
            raise ValueError("M034 termination requires exact/high ownership confidence")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def reconcile_m034_owned_instance(
    *,
    discovery_diff: LambdaM034DiscoveryDiffReport,
    journal_path: str | Path | None = None,
    owned_instance_id: str | None = None,
    planned_shape: str | None = None,
    planned_region: str | None = None,
) -> LambdaM034OwnedInstanceReconciliationReport:
    replay_owned = None
    warnings: list[str] = []
    if journal_path is not None and Path(journal_path).exists():
        replay = replay_m029_launch_journal(journal_path)
        if not replay.replay_passed:
            warnings.append("launch journal replay failed")
        replay_owned = replay.owned_instance_id
    exact_owned = owned_instance_id or replay_owned
    candidates = discovery_diff.possible_owned_candidates
    if exact_owned:
        return LambdaM034OwnedInstanceReconciliationReport(
            owned_instance_id_found=True,
            owned_instance_id_redacted=redact_instance_id(exact_owned),
            candidate_count=len(candidates),
            confidence="exact",
            terminate_allowed=True,
            terminate_allowed_reason="exact owned instance id recorded",
            manual_review_required=False,
            warnings=warnings,
        )
    matching = [
        item
        for item in candidates
        if _matches_planned(item, planned_shape=planned_shape, planned_region=planned_region)
    ]
    if len(matching) == 1 and len(candidates) == 1:
        instance_id = _candidate_id(matching[0])
        return LambdaM034OwnedInstanceReconciliationReport(
            owned_instance_id_found=True,
            owned_instance_id_redacted=redact_instance_id(instance_id),
            candidate_count=1,
            confidence="high",
            terminate_allowed=True,
            terminate_allowed_reason="single candidate matches planned shape and region",
            manual_review_required=False,
            warnings=[*warnings, "ownership inferred from read-only candidate evidence"],
        )
    if not candidates:
        return LambdaM034OwnedInstanceReconciliationReport(
            owned_instance_id_found=False,
            candidate_count=0,
            confidence="none",
            terminate_allowed=False,
            terminate_allowed_reason="no owned candidate visible; no termination target",
            manual_review_required=False,
            warnings=warnings,
        )
    return LambdaM034OwnedInstanceReconciliationReport(
        owned_instance_id_found=False,
        candidate_count=len(candidates),
        confidence="low" if matching else "none",
        terminate_allowed=False,
        terminate_allowed_reason="candidate ownership is ambiguous",
        manual_review_required=True,
        warnings=[*warnings, "ambiguous candidate; do not terminate automatically"],
    )


def reconcile_m034_owned_instance_from_paths(
    *,
    discovery_diff: str | Path,
    journal: str | Path | None = None,
    planned_shape: str | None = None,
    planned_region: str | None = None,
) -> LambdaM034OwnedInstanceReconciliationReport:
    from decodilo.lambda_cloud.m034_discovery_diff import load_lambda_m034_discovery_diff

    return reconcile_m034_owned_instance(
        discovery_diff=load_lambda_m034_discovery_diff(discovery_diff),
        journal_path=journal,
        planned_shape=planned_shape,
        planned_region=planned_region,
    )


def _matches_planned(
    candidate: dict[str, Any],
    *,
    planned_shape: str | None,
    planned_region: str | None,
) -> bool:
    shape = str(candidate.get("instance_type") or candidate.get("shape") or "")
    region = str(candidate.get("region") or "")
    shape_ok = not planned_shape or shape == planned_shape
    region_ok = not planned_region or not region or region == planned_region
    return shape_ok and region_ok


def _candidate_id(candidate: dict[str, Any]) -> str | None:
    value = (
        candidate.get("instance_id")
        or candidate.get("id")
        or candidate.get("name")
        or candidate.get("hostname")
    )
    return None if value is None else str(value)


def load_lambda_m034_owned_instance_reconciliation(
    path: str | Path,
) -> LambdaM034OwnedInstanceReconciliationReport:
    return LambdaM034OwnedInstanceReconciliationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m034_owned_instance_reconciliation(
    path: str | Path,
    report: LambdaM034OwnedInstanceReconciliationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
