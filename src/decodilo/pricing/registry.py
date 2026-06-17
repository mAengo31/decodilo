"""Price snapshot import and query helpers."""

from __future__ import annotations

import json
from pathlib import Path

from decodilo.errors import PricingAmbiguityError
from decodilo.pricing.lambda_prices import load_lambda_prices_from_json, parse_lambda_pricing_html
from decodilo.pricing.snapshots import (
    PriceSnapshot,
    PriceSourceType,
    SnapshotPriceRecord,
    load_price_snapshot,
    make_price_snapshot,
    records_from_price_profiles,
    write_price_snapshot,
)


def import_json_snapshot(
    *,
    provider: str,
    input_path: str | Path,
    output_path: str | Path,
    source_type: PriceSourceType = PriceSourceType.MANUAL_JSON,
    is_sample_data: bool | None = None,
) -> PriceSnapshot:
    profiles = load_lambda_prices_from_json(input_path)
    captured = profiles[0].source_timestamp if profiles else "unknown"
    effective_source_type = PriceSourceType.FIXTURE if is_sample_data is True else source_type
    snapshot = make_price_snapshot(
        provider=provider,
        source_path=input_path,
        source_type=effective_source_type,
        records=records_from_price_profiles(profiles, captured_at_utc=captured),
        is_sample_data=is_sample_data,
    )
    write_price_snapshot(output_path, snapshot)
    return snapshot


def import_html_snapshot(
    *,
    provider: str,
    input_path: str | Path,
    output_path: str | Path,
    source_type: PriceSourceType = PriceSourceType.MANUAL_HTML,
    is_sample_data: bool | None = None,
) -> PriceSnapshot:
    profiles = parse_lambda_pricing_html(input_path, source_url=str(input_path))
    captured = profiles[0].source_timestamp if profiles else "unknown"
    effective_source_type = PriceSourceType.FIXTURE if is_sample_data is True else source_type
    snapshot = make_price_snapshot(
        provider=provider,
        source_path=input_path,
        source_type=effective_source_type,
        records=records_from_price_profiles(profiles, captured_at_utc=captured),
        is_sample_data=is_sample_data,
    )
    write_price_snapshot(output_path, snapshot)
    return snapshot


def query_snapshot_price(
    snapshot: PriceSnapshot,
    *,
    gpu_type: str,
    gpus_per_instance: int,
    instance_type: str | None = None,
    region: str | None = None,
    allow_ambiguous_price: bool = False,
) -> SnapshotPriceRecord:
    matches = [
        record
        for record in snapshot.records
        if record.gpu_type == gpu_type
        and record.gpus_per_instance == gpus_per_instance
        and (instance_type is None or record.instance_type == instance_type)
        and (region is None or record.region == region)
    ]
    if not matches:
        raise PricingAmbiguityError("no snapshot price matched query")
    if len(matches) > 1 and not allow_ambiguous_price:
        raise PricingAmbiguityError(
            "ambiguous snapshot price query; matches="
            + json.dumps([record.record_id for record in matches], sort_keys=True)
        )
    return sorted(matches, key=lambda record: record.record_id)[0]


__all__ = [
    "PriceSourceType",
    "SnapshotPriceRecord",
    "import_html_snapshot",
    "import_json_snapshot",
    "load_price_snapshot",
    "query_snapshot_price",
]
