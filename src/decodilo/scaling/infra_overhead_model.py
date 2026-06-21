"""Combined infrastructure pressure model for learner-pod planning."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from decodilo.scaling.artifact_pressure_model import ArtifactPressureEstimate
from decodilo.scaling.bandwidth_pressure_model import BandwidthPressureEstimate
from decodilo.scaling.syncer_pressure_model import SyncerPressureEstimate


class InfraOverheadEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    infra_efficiency_multiplier: float
    artifact_backend_saturation_ratio: float
    bandwidth_saturation_ratio: float
    syncer_saturation_ratio: float
    dominant_bottleneck: str
    warnings: list[str] = Field(default_factory=list)


def combine_infra_overhead(
    *,
    artifact: ArtifactPressureEstimate,
    bandwidth: BandwidthPressureEstimate,
    syncer: SyncerPressureEstimate,
) -> InfraOverheadEstimate:
    ratios = {
        "artifact_backend": artifact.artifact_backend_saturation_ratio,
        "bandwidth": bandwidth.bandwidth_saturation_ratio,
        "syncer": syncer.syncer_saturation_ratio,
    }
    dominant = max(ratios, key=ratios.get)
    max_ratio = ratios[dominant]
    multiplier = 1.0 if max_ratio <= 1 else 1.0 / (1.0 + (max_ratio - 1.0))
    warnings = [*artifact.warnings, *bandwidth.warnings, *syncer.warnings]
    if max_ratio > 1:
        warnings.append(f"dominant infrastructure bottleneck: {dominant}")
    return InfraOverheadEstimate(
        infra_efficiency_multiplier=max(0.05, min(1.0, multiplier)),
        artifact_backend_saturation_ratio=artifact.artifact_backend_saturation_ratio,
        bandwidth_saturation_ratio=bandwidth.bandwidth_saturation_ratio,
        syncer_saturation_ratio=syncer.syncer_saturation_ratio,
        dominant_bottleneck=dominant,
        warnings=warnings,
    )

