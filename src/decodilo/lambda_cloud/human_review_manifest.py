"""Human review manifest for M026 Lambda implementation decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaM026RequestedDecision = Literal[
    "blocked",
    "needs_more_evidence",
    "approve_m027_minimal_real_mutation_implementation",
]


class LambdaHumanReviewAcknowledgement(BaseModel):
    model_config = ConfigDict(frozen=True)

    understands_future_billable_action: bool = False
    understands_no_launch_in_m026: bool = False
    understands_m027_would_only_implement_code: bool = False
    understands_first_launch_requires_separate_m028_approval: bool = False
    understands_termination_required: bool = False
    understands_os_shutdown_insufficient: bool = False
    understands_max_budget_50: bool = False
    understands_max_runtime_30_min: bool = False
    understands_one_instance_only: bool = False
    understands_no_training: bool = False
    understands_no_ssh: bool = False
    understands_no_setup_scripts: bool = False
    understands_manual_presence_required: bool = False

    def missing(self) -> list[str]:
        return [name for name, value in self.model_dump().items() if not value]


class LambdaHumanReviewManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_schema_version: int = 1
    review_id: str = "lambda-human-review-m026"
    created_at_utc: str | None = None
    reviewer_name: str | None = None
    reviewer_role: str | None = None
    reviewed_evidence_package_hash: str
    reviewed_go_no_go_hash: str
    reviewed_runbook_hash: str = "not-provided"
    reviewed_termination_runbook_hash: str = "not-provided"
    reviewed_spend_safety_hash: str = "not-provided"
    reviewed_semantic_audit_hash: str = "not-provided"
    requested_decision: LambdaM026RequestedDecision = "needs_more_evidence"
    acknowledgements: LambdaHumanReviewAcknowledgement = Field(
        default_factory=LambdaHumanReviewAcknowledgement
    )
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    max_instances: int = 1
    approved_region: str | None = None
    approved_instance_type: str | None = None
    approved_gpu_type: str | None = None
    approved_gpus_per_instance: int | None = None
    notes: str = ""
    human_review_complete: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _review_only(self) -> LambdaHumanReviewManifest:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M026 human review cannot enable launch or mutation")
        if self.max_budget > 50:
            raise ValueError("M026 human review max budget cannot exceed 50")
        if self.max_runtime_minutes > 30:
            raise ValueError("M026 human review runtime cannot exceed 30 minutes")
        if self.max_instances > 1:
            raise ValueError("M026 human review cannot approve more than one instance")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_human_review_manifest(
    *,
    m025_evidence_package: str | Path,
    go_no_go: str | Path,
    acknowledge_all: bool = False,
    requested_decision: LambdaM026RequestedDecision = "needs_more_evidence",
) -> LambdaHumanReviewManifest:
    acknowledgements = LambdaHumanReviewAcknowledgement(
        **{name: acknowledge_all for name in LambdaHumanReviewAcknowledgement.model_fields}
    )
    return LambdaHumanReviewManifest(
        reviewed_evidence_package_hash=_sha256_file(m025_evidence_package),
        reviewed_go_no_go_hash=_sha256_file(go_no_go),
        requested_decision=requested_decision,
        acknowledgements=acknowledgements,
        human_review_complete=acknowledge_all,
    )


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_lambda_human_review_manifest(path: str | Path) -> LambdaHumanReviewManifest:
    return LambdaHumanReviewManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_human_review_manifest(
    path: str | Path,
    manifest: LambdaHumanReviewManifest,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(manifest.to_json(), encoding="utf-8")
