"""Versioned price snapshot models."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.pricing.models import PriceProfile
from decodilo.pricing.provenance import sha256_file, utc_now_iso

PRICE_SNAPSHOT_SCHEMA_VERSION = "v1"


class PriceSourceType(str, Enum):
    FIXTURE = "fixture"
    MANUAL_HTML = "manual_html"
    MANUAL_JSON = "manual_json"
    PUBLIC_WEB = "public_web"


class SnapshotPriceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    product_family: str = "unknown"
    instance_type: str
    gpu_type: str
    gpus_per_instance: int = Field(gt=0)
    gpu_memory_gb: float | None = None
    region: str | None = None
    commitment_term: str | None = None
    price_per_gpu_hour: float = Field(ge=0)
    price_per_instance_hour: float = Field(ge=0)
    currency: str = "USD"
    tax_included: bool = False
    source_url: str | None = None
    captured_at_utc: str
    record_id: str

    def to_price_profile(self) -> PriceProfile:
        return PriceProfile(
            provider=self.provider,
            instance_type=self.instance_type,
            gpu_type=self.gpu_type,
            gpus_per_instance=self.gpus_per_instance,
            gpu_memory_gb=self.gpu_memory_gb or 0.01,
            price_per_gpu_hour=self.price_per_gpu_hour,
            price_per_instance_hour=self.price_per_instance_hour,
            region=self.region,
            source_url=self.source_url or "price-snapshot",
            source_timestamp=self.captured_at_utc,
            tax_included=self.tax_included,
        )


class PriceSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = PRICE_SNAPSHOT_SCHEMA_VERSION
    snapshot_id: str
    provider: str
    captured_at_utc: str
    source_url: str | None = None
    source_type: PriceSourceType
    source_sha256: str
    parser_version: str = "v1"
    currency: str = "USD"
    tax_included: bool = False
    records: list[SnapshotPriceRecord]
    notes: str = ""
    is_sample_data: bool = False


def records_from_price_profiles(
    profiles: list[PriceProfile],
    *,
    captured_at_utc: str,
    currency: str = "USD",
) -> list[SnapshotPriceRecord]:
    records: list[SnapshotPriceRecord] = []
    for index, profile in enumerate(profiles):
        records.append(
            SnapshotPriceRecord(
                provider=profile.provider,
                product_family="instances",
                instance_type=profile.instance_type,
                gpu_type=profile.gpu_type,
                gpus_per_instance=profile.gpus_per_instance,
                gpu_memory_gb=profile.gpu_memory_gb,
                region=profile.region,
                price_per_gpu_hour=profile.price_per_gpu_hour,
                price_per_instance_hour=profile.price_per_instance_hour,
                currency=currency,
                tax_included=profile.tax_included,
                source_url=profile.source_url,
                captured_at_utc=captured_at_utc,
                record_id=f"{profile.provider}:{profile.instance_type}:{index}",
            )
        )
    return records


def make_price_snapshot(
    *,
    provider: str,
    source_path: str | Path,
    source_type: PriceSourceType,
    records: list[SnapshotPriceRecord],
    source_url: str | None = None,
    captured_at_utc: str | None = None,
    notes: str = "",
    is_sample_data: bool | None = None,
) -> PriceSnapshot:
    captured = captured_at_utc or utc_now_iso()
    source_hash = sha256_file(source_path)
    snapshot_id = f"{provider}-{source_hash[:12]}-{captured[:10]}"
    return PriceSnapshot(
        snapshot_id=snapshot_id,
        provider=provider,
        captured_at_utc=captured,
        source_url=source_url or str(source_path),
        source_type=source_type,
        source_sha256=source_hash,
        records=records,
        tax_included=any(record.tax_included for record in records),
        notes=notes,
        is_sample_data=(source_type == PriceSourceType.FIXTURE)
        if is_sample_data is None
        else is_sample_data,
    )


def write_price_snapshot(path: str | Path, snapshot: PriceSnapshot) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_price_snapshot(path: str | Path) -> PriceSnapshot:
    return PriceSnapshot.model_validate_json(Path(path).read_text(encoding="utf-8"))

