"""Resolve a first-launch Lambda shape from catalog, price, and availability evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.availability_evidence import (
    LambdaAvailabilityEvidence,
    load_lambda_availability_evidence,
)
from decodilo.lambda_cloud.product_catalog_evidence import (
    LambdaProductCatalogEvidenceReport,
    LambdaProductCatalogRecord,
)
from decodilo.lambda_cloud.shape_evidence import LambdaShapeEvidence, LambdaShapeEvidenceReport
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

LambdaLaunchShapeResolutionStatus = Literal[
    "resolved",
    "unresolved_missing_price",
    "unresolved_missing_product_catalog",
    "unresolved_ambiguous",
    "unresolved_operator_confirmation_required",
]


class LambdaPlannedLaunchShape(BaseModel):
    model_config = ConfigDict(frozen=True)

    gpu_type: str
    gpus_per_instance: int = Field(gt=0)
    instance_type_or_shape: str
    region: str | None = None


class LambdaLaunchShapeResolutionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    planned_gpu_type: str
    planned_gpus_per_instance: int
    planned_instance_type_or_shape: str
    planned_region: str | None = None
    matched_product_catalog_record: dict[str, Any] | None = None
    matched_price_record: dict[str, Any] | None = None
    live_availability_status: str
    shape_resolution_status: LambdaLaunchShapeResolutionStatus
    first_launch_allowed_by_shape_evidence: bool
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def resolve_lambda_launch_shape(
    *,
    planned_shape: LambdaPlannedLaunchShape,
    catalog_records: list[LambdaProductCatalogRecord | LambdaShapeEvidence],
    price_snapshot: PriceSnapshot,
    availability: LambdaAvailabilityEvidence,
    operator_confirmed_shape: bool = True,
) -> LambdaLaunchShapeResolutionReport:
    catalog_matches = _catalog_matches(catalog_records, planned_shape)
    price_matches = _price_matches(price_snapshot.records, planned_shape)
    warnings = [*availability.warnings]
    limitations = [*availability.limitations]
    errors: list[str] = []
    status: LambdaLaunchShapeResolutionStatus = "resolved"
    if not operator_confirmed_shape:
        status = "unresolved_operator_confirmation_required"
        errors.append("operator selected shape confirmation missing")
    elif len(catalog_matches) != 1:
        status = (
            "unresolved_missing_product_catalog"
            if not catalog_matches
            else "unresolved_ambiguous"
        )
        errors.append("product catalog shape evidence missing or ambiguous")
    elif len(price_matches) != 1:
        status = "unresolved_missing_price" if not price_matches else "unresolved_ambiguous"
        errors.append("non-sample price evidence missing or ambiguous")
    elif price_snapshot.is_sample_data:
        status = "unresolved_missing_price"
        errors.append("sample price snapshot cannot support first launch")
    if availability.status in {"unknown", "endpoint_inconclusive", "unsupported_endpoint"}:
        warnings.append("live availability remains unknown until launch attempt")
    elif availability.status == "unavailable":
        errors.append("live availability evidence says planned shape is unavailable")
        status = "unresolved_missing_product_catalog"
    product = catalog_matches[0] if len(catalog_matches) == 1 else None
    price = price_matches[0] if len(price_matches) == 1 else None
    resolved = status == "resolved" and not errors
    return LambdaLaunchShapeResolutionReport(
        planned_gpu_type=planned_shape.gpu_type,
        planned_gpus_per_instance=planned_shape.gpus_per_instance,
        planned_instance_type_or_shape=planned_shape.instance_type_or_shape,
        planned_region=planned_shape.region,
        matched_product_catalog_record=None
        if product is None
        else product.model_dump(mode="json"),
        matched_price_record=None if price is None else price.model_dump(mode="json"),
        live_availability_status=availability.status,
        shape_resolution_status=status,
        first_launch_allowed_by_shape_evidence=resolved,
        limitations=limitations,
        warnings=sorted(set(warnings)),
        errors=errors,
    )


def planned_shape_from_m020_report(path: str | Path) -> LambdaPlannedLaunchShape:
    from decodilo.lambda_cloud.m020_report import load_lambda_m020_report

    report = load_lambda_m020_report(path)
    price = report.price_reconciliation
    return LambdaPlannedLaunchShape(
        gpu_type=price.selected_gpu_type,
        gpus_per_instance=price.selected_gpus_per_instance,
        instance_type_or_shape=(
            price.shape_match.requested_instance_type
            or price.shape_match.matched_instance_type
            or "unknown"
        ),
        region=price.selected_region,
    )


def load_planned_shape(path: str | Path) -> LambdaPlannedLaunchShape:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "price_reconciliation" in payload:
        return planned_shape_from_m020_report(path)
    return LambdaPlannedLaunchShape.model_validate(payload)


def resolve_lambda_launch_shape_from_paths(
    *,
    planned_shape_path: str | Path,
    catalog_evidence: str | Path,
    price_snapshot: str | Path,
    availability_evidence: str | Path,
) -> LambdaLaunchShapeResolutionReport:
    catalog_records = _load_catalog_records(catalog_evidence)
    return resolve_lambda_launch_shape(
        planned_shape=load_planned_shape(planned_shape_path),
        catalog_records=catalog_records,
        price_snapshot=load_price_snapshot(price_snapshot),
        availability=load_lambda_availability_evidence(availability_evidence),
        operator_confirmed_shape=True,
    )


def _load_catalog_records(
    path: str | Path,
) -> list[LambdaProductCatalogRecord | LambdaShapeEvidence]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "records" in payload:
        return LambdaProductCatalogEvidenceReport.model_validate(payload).records
    if "evidence" in payload:
        report = LambdaShapeEvidenceReport.model_validate(payload)
        return [
            item
            for item in report.evidence
            if item.is_product_catalog_evidence and not item.is_sample_data
        ]
    raise ValueError("catalog evidence must be product catalog or shape evidence JSON")


def _catalog_matches(
    records: list[LambdaProductCatalogRecord | LambdaShapeEvidence],
    planned: LambdaPlannedLaunchShape,
) -> list[LambdaProductCatalogRecord | LambdaShapeEvidence]:
    return [
        record
        for record in records
        if record.gpu_type == planned.gpu_type
        and record.gpus_per_instance == planned.gpus_per_instance
        and _catalog_instance_type(record) == planned.instance_type_or_shape
    ]


def _catalog_instance_type(record: LambdaProductCatalogRecord | LambdaShapeEvidence) -> str:
    if isinstance(record, LambdaProductCatalogRecord):
        return record.instance_type
    return record.instance_type_or_shape


def _price_matches(
    records: list[SnapshotPriceRecord],
    planned: LambdaPlannedLaunchShape,
) -> list[SnapshotPriceRecord]:
    return [
        record
        for record in records
        if record.gpu_type == planned.gpu_type
        and record.gpus_per_instance == planned.gpus_per_instance
        and record.instance_type == planned.instance_type_or_shape
    ]


def load_lambda_launch_shape_resolution_report(
    path: str | Path,
) -> LambdaLaunchShapeResolutionReport:
    return LambdaLaunchShapeResolutionReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_launch_shape_resolution_report(
    path: str | Path,
    report: LambdaLaunchShapeResolutionReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
