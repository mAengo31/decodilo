"""Typed price records for offline cost estimation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PriceProfile(BaseModel):
    """A normalized accelerator price record."""

    model_config = ConfigDict(frozen=True)

    provider: str
    instance_type: str
    gpu_type: str
    gpus_per_instance: int = Field(gt=0)
    gpu_memory_gb: float = Field(gt=0)
    price_per_gpu_hour: float = Field(ge=0)
    price_per_instance_hour: float = Field(ge=0)
    region: str | None = None
    source_url: str
    source_timestamp: str
    tax_included: bool = False
    notes: str = ""

