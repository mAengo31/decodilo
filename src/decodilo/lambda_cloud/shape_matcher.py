"""Read-only Lambda shape matching against discovery and price snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.api_models import LambdaInstanceType
from decodilo.lambda_cloud.discovery import LambdaDiscoveryReport, load_lambda_discovery_report
from decodilo.lambda_cloud.launch_plan import LambdaLaunchPlan, load_lambda_launch_plan
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

LambdaShapeMatchStatus = Literal[
    "matched",
    "discovered_but_no_price",
    "priced_but_not_discovered",
    "ambiguous",
    "missing",
]


class LambdaShapeMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    requested_gpu_type: str
    requested_gpus_per_instance: int
    requested_region: str
    requested_instance_type: str | None = None
    matched_instance_type: str | None = None
    matched_shape: dict | None = None
    matched_price_record_id: str | None = None
    price_per_gpu_hour: float | None = None
    price_per_instance_hour: float | None = None
    discovery_source: str
    live_api_used: bool
    price_snapshot_id: str
    match_status: LambdaShapeMatchStatus
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaShapeMatchReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    matches: list[LambdaShapeMatch]
    matched: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def match_lambda_shape(
    *,
    discovery: LambdaLiveDiscoveryReport | LambdaDiscoveryReport,
    price_snapshot: PriceSnapshot,
    requested_gpu_type: str,
    requested_gpus_per_instance: int,
    requested_region: str,
    requested_instance_type: str | None = None,
    live_instance_types_endpoint_inconclusive: bool = False,
) -> LambdaShapeMatch:
    shapes = _instance_types(discovery)
    discovered = _matching_discovered_shapes(
        shapes,
        gpu_type=requested_gpu_type,
        gpus=requested_gpus_per_instance,
        region=requested_region,
        instance_type=requested_instance_type,
    )
    prices = _matching_price_records(
        price_snapshot,
        gpu_type=requested_gpu_type,
        gpus=requested_gpus_per_instance,
        instance_type=requested_instance_type,
    )
    warnings: list[str] = []
    errors: list[str] = []
    status: LambdaShapeMatchStatus
    chosen_shape: LambdaInstanceType | None = None
    chosen_price: SnapshotPriceRecord | None = None
    if len(discovered) > 1 or len(prices) > 1:
        status = "ambiguous"
        errors.append("ambiguous Lambda shape or price match")
    elif discovered and prices:
        chosen_shape = discovered[0]
        chosen_price = prices[0]
        status = "matched"
        if chosen_price.region and chosen_price.region not in {
            requested_region,
            "sample-offline",
            "unknown",
        }:
            warnings.append(
                "price record region differs from requested region; using manual snapshot price"
            )
    elif discovered and not prices:
        chosen_shape = discovered[0]
        status = "discovered_but_no_price"
        errors.append("discovered Lambda shape has no matching price snapshot record")
    elif prices and not discovered and live_instance_types_endpoint_inconclusive and not shapes:
        chosen_price = prices[0]
        status = "matched"
        warnings.append(
            "price snapshot shape was not present in live API instance-type results; "
            "endpoint semantics are inconclusive"
        )
    elif prices and not discovered:
        chosen_price = prices[0]
        status = "priced_but_not_discovered"
        warnings.append("price snapshot shape was not present in read-only discovery")
        errors.append("planned shape was not discovered by Lambda read-only discovery")
    else:
        status = "missing"
        errors.append("planned Lambda shape missing from discovery and price snapshot")
    return LambdaShapeMatch(
        requested_gpu_type=requested_gpu_type,
        requested_gpus_per_instance=requested_gpus_per_instance,
        requested_region=requested_region,
        requested_instance_type=requested_instance_type,
        matched_instance_type=_shape_id(chosen_shape)
        or (chosen_price.instance_type if chosen_price else None),
        matched_shape=None if chosen_shape is None else chosen_shape.model_dump(mode="json"),
        matched_price_record_id=None if chosen_price is None else chosen_price.record_id,
        price_per_gpu_hour=None if chosen_price is None else chosen_price.price_per_gpu_hour,
        price_per_instance_hour=None
        if chosen_price is None
        else chosen_price.price_per_instance_hour,
        discovery_source=getattr(discovery, "source", "unknown"),
        live_api_used=bool(getattr(discovery, "live_api_used", False)),
        price_snapshot_id=price_snapshot.snapshot_id,
        match_status=status,
        warnings=warnings,
        errors=errors,
    )


def build_lambda_shape_match_report(
    *,
    discovery: LambdaLiveDiscoveryReport | LambdaDiscoveryReport,
    price_snapshot: PriceSnapshot,
    launch_plan: LambdaLaunchPlan,
    gpu_type: str,
    gpus_per_instance: int | None = None,
    live_instance_types_endpoint_inconclusive: bool = False,
) -> LambdaShapeMatchReport:
    requested_gpus = gpus_per_instance or (
        launch_plan.nodes[0].gpus_per_instance if launch_plan.nodes else 0
    )
    match = match_lambda_shape(
        discovery=discovery,
        price_snapshot=price_snapshot,
        requested_gpu_type=gpu_type,
        requested_gpus_per_instance=requested_gpus,
        requested_region=launch_plan.region,
        requested_instance_type=launch_plan.instance_type,
        live_instance_types_endpoint_inconclusive=live_instance_types_endpoint_inconclusive,
    )
    return LambdaShapeMatchReport(
        matches=[match],
        matched=match.match_status == "matched",
        warnings=match.warnings,
        errors=match.errors,
    )


def load_discovery_any(path: str | Path) -> LambdaLiveDiscoveryReport | LambdaDiscoveryReport:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if (
        payload.get("source") in {"live_read_only", "fake_transport"}
        and "endpoint_results" in payload
    ):
        return load_lambda_live_discovery_report(path)
    return load_lambda_discovery_report(path)


def match_lambda_shape_from_paths(
    *,
    discovery_report: str | Path,
    price_snapshot: str | Path,
    launch_plan: str | Path,
    gpu_type: str,
    gpus_per_instance: int | None = None,
) -> LambdaShapeMatchReport:
    return build_lambda_shape_match_report(
        discovery=load_discovery_any(discovery_report),
        price_snapshot=load_price_snapshot(price_snapshot),
        launch_plan=load_lambda_launch_plan(launch_plan),
        gpu_type=gpu_type,
        gpus_per_instance=gpus_per_instance,
    )


def _instance_types(
    discovery: LambdaLiveDiscoveryReport | LambdaDiscoveryReport,
) -> list[LambdaInstanceType]:
    return list(getattr(discovery, "instance_types", []))


def _shape_id(shape: LambdaInstanceType | None) -> str | None:
    if shape is None:
        return None
    return shape.instance_type_id or shape.name


def _matching_discovered_shapes(
    shapes: list[LambdaInstanceType],
    *,
    gpu_type: str,
    gpus: int,
    region: str,
    instance_type: str | None,
) -> list[LambdaInstanceType]:
    matches = []
    for shape in shapes:
        ids = {shape.instance_type_id, shape.name}
        region_matches = not shape.regions or region in shape.regions
        if (
            shape.gpu_type == gpu_type
            and shape.gpus == gpus
            and region_matches
            and (instance_type is None or instance_type in ids)
        ):
            matches.append(shape)
    return matches


def _matching_price_records(
    snapshot: PriceSnapshot,
    *,
    gpu_type: str,
    gpus: int,
    instance_type: str | None,
) -> list[SnapshotPriceRecord]:
    return [
        record
        for record in snapshot.records
        if record.gpu_type == gpu_type
        and record.gpus_per_instance == gpus
        and (instance_type is None or record.instance_type == instance_type)
    ]


def write_lambda_shape_match_report(path: str | Path, report: LambdaShapeMatchReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
