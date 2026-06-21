"""Review record for M023 Lambda real mutation design artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.first_launch_evidence_package import (
    LambdaFirstLaunchEvidencePackage,
    load_lambda_first_launch_evidence_package,
)

LambdaRealMutationReviewStatus = Literal[
    "not_ready",
    "evidence_incomplete",
    "design_review_ready",
    "blocked",
]


class LambdaRealMutationReviewRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    review_id: str = "lambda-real-mutation-review-record-m023"
    evidence_package_ref: str
    status: LambdaRealMutationReviewStatus
    rationale: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    human_review_required: bool = True
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _never_enable(self) -> LambdaRealMutationReviewRecord:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M023 review record cannot enable mutation or launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_real_mutation_review_record(
    *,
    evidence_package: str | Path | LambdaFirstLaunchEvidencePackage,
) -> LambdaRealMutationReviewRecord:
    if isinstance(evidence_package, LambdaFirstLaunchEvidencePackage):
        package = evidence_package
        ref = "<in-memory>"
    else:
        package = load_lambda_first_launch_evidence_package(evidence_package)
        ref = str(evidence_package)
    if package.blockers:
        status: LambdaRealMutationReviewStatus = (
            "evidence_incomplete"
            if any(blocker.startswith("missing evidence") for blocker in package.blockers)
            else "blocked"
        )
        rationale = "Required real mutation design review evidence is incomplete or blocked."
    elif package.evidence_complete:
        status = "design_review_ready"
        rationale = (
            "Design evidence is complete enough for human review; "
            "real mutation remains disabled."
        )
    else:
        status = "not_ready"
        rationale = "Evidence package is not complete."
    warnings = [
        "design review ready only; real mutation remains disabled",
        *package.warnings,
    ]
    return LambdaRealMutationReviewRecord(
        evidence_package_ref=ref,
        status=status,
        rationale=rationale,
        blockers=package.blockers,
        warnings=warnings,
    )


def load_lambda_real_mutation_review_record(path: str | Path) -> LambdaRealMutationReviewRecord:
    return LambdaRealMutationReviewRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_real_mutation_review_record(
    path: str | Path,
    record: LambdaRealMutationReviewRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
