"""Evidence records for Lambda launch shapes and prices."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaShapeEvidenceSource = Literal[
    "live_api_discovery",
    "public_product_catalog",
    "manual_operator_catalog",
    "price_snapshot",
    "planned_launch_shape",
]
LambdaShapeEvidenceStatus = Literal["accepted", "blocked", "inconclusive"]
LambdaShapeEvidenceConfidence = Literal["low", "medium", "high"]


class LambdaShapeEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    gpu_type: str
    gpus_per_instance: int = Field(gt=0)
    instance_type_or_shape: str
    region: str | None = None
    source_type: LambdaShapeEvidenceSource
    source_url: str | None = None
    captured_at_utc: str | None = None
    source_hash: str
    is_live_availability_evidence: bool = False
    is_product_catalog_evidence: bool = False
    is_price_evidence: bool = False
    is_sample_data: bool = False
    confidence: LambdaShapeEvidenceConfidence = "medium"
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaShapeEvidence:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("shape evidence cannot enable launch or record billable action")
        if self.source_type == "public_product_catalog" and self.is_live_availability_evidence:
            raise ValueError("public product catalog is not live availability evidence")
        if self.is_sample_data and self.confidence == "high":
            raise ValueError("sample shape evidence cannot have high confidence")
        return self


class LambdaShapeEvidenceReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    evidence: list[LambdaShapeEvidence] = Field(default_factory=list)
    evidence_status: LambdaShapeEvidenceStatus
    first_launch_evidence_usable: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaShapeEvidenceReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("shape evidence report cannot enable launch or billable action")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_shape_evidence_report(
    evidence: list[LambdaShapeEvidence],
    *,
    require_non_sample: bool = True,
) -> LambdaShapeEvidenceReport:
    blockers: list[str] = []
    warnings: list[str] = []
    if not evidence:
        blockers.append("shape evidence missing")
    if require_non_sample and any(item.is_sample_data for item in evidence):
        blockers.append("sample evidence cannot support first launch")
    if not any(item.is_product_catalog_evidence for item in evidence):
        warnings.append("no product catalog evidence present")
    if not any(item.is_live_availability_evidence for item in evidence):
        warnings.append("no live availability proof present")
    status: LambdaShapeEvidenceStatus
    if blockers:
        status = "blocked"
    elif warnings:
        status = "inconclusive"
    else:
        status = "accepted"
    return LambdaShapeEvidenceReport(
        evidence=evidence,
        evidence_status=status,
        first_launch_evidence_usable=not blockers,
        blockers=blockers,
        warnings=warnings,
    )


def source_hash_for_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_hash_for_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_lambda_shape_evidence_report(path: str | Path) -> LambdaShapeEvidenceReport:
    return LambdaShapeEvidenceReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_shape_evidence_report(
    path: str | Path,
    report: LambdaShapeEvidenceReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
