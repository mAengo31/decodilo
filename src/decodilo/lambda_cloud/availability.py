"""Planning-only Lambda availability helpers from fake discovery reports."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.discovery import LambdaDiscoveryReport


class LambdaAvailabilityEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    region_id: str
    matching_instance_type_ids: list[str] = Field(default_factory=list)
    available: bool
    live_api_used: bool = False
    warnings: list[str] = Field(default_factory=list)


def estimate_lambda_availability(
    discovery: LambdaDiscoveryReport,
    *,
    region_id: str,
    gpu_type: str | None = None,
    gpus_per_instance: int | None = None,
) -> LambdaAvailabilityEstimate:
    available_regions = {region.region_id for region in discovery.regions if region.available}
    matches = []
    for item in discovery.instance_types:
        if region_id not in item.regions:
            continue
        if gpu_type is not None and item.gpu_type != gpu_type:
            continue
        if gpus_per_instance is not None and item.gpus != gpus_per_instance:
            continue
        matches.append(item.instance_type_id)
    warnings = ["fixture availability is not live Lambda capacity"]
    return LambdaAvailabilityEstimate(
        region_id=region_id,
        matching_instance_type_ids=matches,
        available=region_id in available_regions and bool(matches),
        warnings=warnings,
    )
