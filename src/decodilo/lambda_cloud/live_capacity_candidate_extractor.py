"""Extract availability-first Lambda launch candidates from read-only evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.pricing.snapshots import PriceSnapshot, load_price_snapshot

LambdaAvailabilityStatus = Literal[
    "live_available",
    "live_unavailable",
    "endpoint_inconclusive",
    "unsupported",
]


class LambdaCapacityCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    shape: str
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    region: str | None = None
    price_per_instance_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    source: Literal["live_instance_types", "product_catalog"]
    live_available: bool = False
    strand_payload_compatible: bool = True
    filesystem_required: bool = False


class LambdaLiveCapacityCandidateExtractorReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    live_candidates: list[LambdaCapacityCandidate] = Field(default_factory=list)
    product_catalog_candidates: list[LambdaCapacityCandidate] = Field(default_factory=list)
    availability_status: LambdaAvailabilityStatus
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLiveCapacityCandidateExtractorReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("capacity candidate extraction cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def extract_lambda_capacity_candidates(
    *,
    discovery: LambdaLiveDiscoveryReport,
    price_snapshot: PriceSnapshot,
    planned_hours: float = 0.5,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaLiveCapacityCandidateExtractorReport:
    errors: list[str] = []
    if price_snapshot.is_sample_data:
        errors.append("sample_price_snapshot_cannot_rank_capacity_candidates")
    live_candidates = [
        LambdaCapacityCandidate(
            shape=item.name or item.instance_type_id,
            gpu_type=item.gpu_type,
            gpus_per_instance=item.gpus or None,
            region=(item.regions[0] if item.regions else None),
            price_per_instance_hour=item.price_per_hour,
            estimated_30min_cost=_estimate(item.price_per_hour, planned_hours),
            buffered_estimated_30min_cost=_buffered(
                item.price_per_hour,
                planned_hours,
                safety_buffer_multiplier,
            ),
            source="live_instance_types",
            live_available=True,
        )
        for item in discovery.instance_types
    ]
    catalog_candidates = [
        LambdaCapacityCandidate(
            shape=record.instance_type,
            gpu_type=record.gpu_type,
            gpus_per_instance=record.gpus_per_instance,
            region=record.region,
            price_per_instance_hour=record.price_per_instance_hour,
            estimated_30min_cost=_estimate(record.price_per_instance_hour, planned_hours),
            buffered_estimated_30min_cost=_buffered(
                record.price_per_instance_hour,
                planned_hours,
                safety_buffer_multiplier,
            ),
            source="product_catalog",
            live_available=False,
        )
        for record in price_snapshot.records
        if record.provider == "lambda"
    ]
    if live_candidates:
        availability_status: LambdaAvailabilityStatus = "live_available"
    elif _instance_type_endpoint_attempted(discovery) or discovery.required_endpoint_success:
        availability_status = "endpoint_inconclusive"
    else:
        availability_status = "unsupported"
    return LambdaLiveCapacityCandidateExtractorReport(
        live_candidates=live_candidates,
        product_catalog_candidates=catalog_candidates,
        availability_status=availability_status,
        limitations=[
            "read-only instance-type evidence may not represent instantaneous capacity",
            "catalog candidates are price evidence, not live availability evidence",
        ],
        warnings=[
            (
                "zero live instance-type candidates is endpoint_inconclusive "
                "when endpoint semantics are uncertain"
            )
        ],
        errors=errors,
    )


def extract_lambda_capacity_candidates_from_paths(
    *,
    discovery_report: str | Path,
    price_snapshot: str | Path,
) -> LambdaLiveCapacityCandidateExtractorReport:
    return extract_lambda_capacity_candidates(
        discovery=load_lambda_live_discovery_report(discovery_report),
        price_snapshot=load_price_snapshot(price_snapshot),
    )


def _estimate(price_per_hour: float | None, hours: float) -> float | None:
    return None if price_per_hour is None else round(price_per_hour * hours, 8)


def _buffered(
    price_per_hour: float | None,
    hours: float,
    multiplier: float,
) -> float | None:
    estimate = _estimate(price_per_hour, hours)
    return None if estimate is None else round(estimate * multiplier, 8)


def _instance_type_endpoint_attempted(discovery: LambdaLiveDiscoveryReport) -> bool:
    return any(
        "instance" in result.operation.lower() and "type" in result.operation.lower()
        for result in discovery.endpoint_results
    ) or discovery.endpoint_count_attempted > 0


def load_lambda_live_capacity_candidate_extractor(
    path: str | Path,
) -> LambdaLiveCapacityCandidateExtractorReport:
    return LambdaLiveCapacityCandidateExtractorReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_live_capacity_candidate_extractor(
    path: str | Path,
    report: LambdaLiveCapacityCandidateExtractorReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
