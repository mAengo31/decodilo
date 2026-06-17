"""Static Lambda planning shape catalog.

The entries in this module are advisory planning metadata only. They are not
live availability and they intentionally contain no prices.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from decodilo.errors import PricingAmbiguityError


class LambdaShape(BaseModel):
    model_config = ConfigDict(frozen=True)

    shape: str
    gpu_type: str
    gpus_per_instance: int = Field(gt=0)
    gpu_memory_gb: float | None = None
    notes: str = "planning metadata only; live availability is unknown"
    supported_regions: list[str] = Field(default_factory=list)


class LambdaShapeCatalog:
    """Small static catalog for dry-run planning."""

    def __init__(self, shapes: list[LambdaShape] | None = None) -> None:
        self.shapes = shapes if shapes is not None else [
            LambdaShape(
                shape="gpu_8x_h100_sxm",
                gpu_type="H100 SXM",
                gpus_per_instance=8,
                gpu_memory_gb=80,
            ),
            LambdaShape(
                shape="gpu_8x_a100_sxm",
                gpu_type="A100 SXM",
                gpus_per_instance=8,
                gpu_memory_gb=80,
            ),
            LambdaShape(
                shape="gpu_1x_h100_sxm",
                gpu_type="H100 SXM",
                gpus_per_instance=1,
                gpu_memory_gb=80,
            ),
        ]

    def lookup(
        self,
        *,
        gpu_type: str,
        gpus_per_instance: int,
        shape: str | None = None,
        allow_ambiguous_shape: bool = False,
    ) -> LambdaShape:
        matches = [
            entry
            for entry in self.shapes
            if entry.gpu_type == gpu_type
            and entry.gpus_per_instance == gpus_per_instance
            and (shape is None or entry.shape == shape)
        ]
        if not matches:
            raise PricingAmbiguityError("no Lambda planning shape matched query")
        if len(matches) > 1 and not allow_ambiguous_shape:
            raise PricingAmbiguityError("ambiguous Lambda planning shape query")
        return sorted(matches, key=lambda item: item.shape)[0]
