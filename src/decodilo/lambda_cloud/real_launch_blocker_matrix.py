"""Blocker matrix for M026 Lambda real-launch decision review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.evidence_freshness import (
    LambdaEvidenceFreshnessReport,
    load_lambda_evidence_freshness_report,
)
from decodilo.lambda_cloud.human_review_validator import (
    LambdaHumanReviewValidationReport,
    load_lambda_human_review_validation_report,
)
from decodilo.lambda_cloud.semantic_mutation_audit import (
    LambdaSemanticMutationAuditReport,
    load_lambda_semantic_mutation_audit_report,
)

LambdaRealLaunchBlockerSeverity = Literal["info", "warning", "blocker", "critical"]


class LambdaRealLaunchBlocker(BaseModel):
    model_config = ConfigDict(frozen=True)

    blocker_id: str
    category: str
    severity: LambdaRealLaunchBlockerSeverity
    message: str
    blocks_m027_implementation_authorization: bool
    blocks_real_launch_execution: bool = True


class LambdaRealLaunchBlockerMatrix(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    blockers: list[LambdaRealLaunchBlocker]
    m027_authorization_blocked: bool
    real_launch_execution_blocked: bool = True
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_real_launch_blocker_matrix(
    *,
    human_review_validation: str | Path | LambdaHumanReviewValidationReport | None = None,
    freshness_report: str | Path | LambdaEvidenceFreshnessReport | None = None,
    semantic_audit: str | Path | LambdaSemanticMutationAuditReport | None = None,
) -> LambdaRealLaunchBlockerMatrix:
    human = _load_human(human_review_validation)
    freshness = _load_freshness(freshness_report)
    semantic = _load_semantic(semantic_audit)
    blockers: list[LambdaRealLaunchBlocker] = [
        LambdaRealLaunchBlocker(
            blocker_id="m026_cannot_enable_launch",
            category="m026_cannot_enable_launch",
            severity="critical",
            message="M026 can authorize implementation review only, not execution.",
            blocks_m027_implementation_authorization=False,
        ),
        LambdaRealLaunchBlocker(
            blocker_id="launch_disabled_by_policy",
            category="launch_disabled_by_policy",
            severity="critical",
            message="Launch remains disabled by current policy.",
            blocks_m027_implementation_authorization=False,
        ),
        LambdaRealLaunchBlocker(
            blocker_id="launch_execution_not_implemented",
            category="launch_execution_not_implemented",
            severity="critical",
            message="Real launch execution is not implemented.",
            blocks_m027_implementation_authorization=False,
        ),
    ]
    if human is None:
        blockers.append(_m027_blocker("missing_human_review", "human review missing"))
    elif not human.human_review_valid_for_m027_authorization:
        blockers.append(_m027_blocker("incomplete_human_review", "human review incomplete"))
    if freshness is None:
        blockers.append(_m027_blocker("stale_live_discovery", "freshness report missing"))
    elif not freshness.freshness_passed:
        category = "stale_live_discovery" if freshness.stale_items else "missing_evidence"
        blockers.append(_m027_blocker(category, "freshness evidence did not pass"))
    if semantic is None:
        blockers.append(_m027_blocker("semantic_mutation_audit_failed", "semantic audit missing"))
    elif not semantic.passed:
        blockers.append(_m027_blocker("semantic_mutation_audit_failed", "semantic audit failed"))
    m027_blocked = any(blocker.blocks_m027_implementation_authorization for blocker in blockers)
    return LambdaRealLaunchBlockerMatrix(
        blockers=blockers,
        m027_authorization_blocked=m027_blocked,
        warnings=[
            "Real launch execution blockers always remain present in M026.",
        ],
    )


def _m027_blocker(category: str, message: str) -> LambdaRealLaunchBlocker:
    return LambdaRealLaunchBlocker(
        blocker_id=category,
        category=category,
        severity="blocker",
        message=message,
        blocks_m027_implementation_authorization=True,
        blocks_real_launch_execution=True,
    )


def _load_human(
    value: str | Path | LambdaHumanReviewValidationReport | None,
) -> LambdaHumanReviewValidationReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaHumanReviewValidationReport):
        return value
    return load_lambda_human_review_validation_report(value)


def _load_freshness(
    value: str | Path | LambdaEvidenceFreshnessReport | None,
) -> LambdaEvidenceFreshnessReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaEvidenceFreshnessReport):
        return value
    return load_lambda_evidence_freshness_report(value)


def _load_semantic(
    value: str | Path | LambdaSemanticMutationAuditReport | None,
) -> LambdaSemanticMutationAuditReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaSemanticMutationAuditReport):
        return value
    return load_lambda_semantic_mutation_audit_report(value)


def load_lambda_real_launch_blocker_matrix(path: str | Path) -> LambdaRealLaunchBlockerMatrix:
    return LambdaRealLaunchBlockerMatrix.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_real_launch_blocker_matrix(
    path: str | Path,
    matrix: LambdaRealLaunchBlockerMatrix,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(matrix.to_json(), encoding="utf-8")
