"""Import Lambda product catalog evidence into price snapshots."""

from __future__ import annotations

from pathlib import Path

from decodilo.lambda_cloud.product_catalog_evidence import (
    LambdaProductCatalogEvidenceReport,
    import_lambda_product_catalog_html,
    import_lambda_product_catalog_json,
)
from decodilo.pricing.snapshots import (
    PriceSnapshot,
    PriceSourceType,
    SnapshotPriceRecord,
    make_price_snapshot,
    write_price_snapshot,
)


def price_snapshot_from_product_catalog(
    catalog: LambdaProductCatalogEvidenceReport,
    *,
    source_path: str | Path,
) -> PriceSnapshot:
    records = [
        SnapshotPriceRecord(
            provider=record.provider,
            product_family=record.product_family,
            instance_type=record.instance_type,
            gpu_type=record.gpu_type,
            gpus_per_instance=record.gpus_per_instance,
            gpu_memory_gb=record.gpu_memory_gb,
            region=None,
            price_per_gpu_hour=record.price_per_gpu_hour,
            price_per_instance_hour=record.price_per_instance_hour,
            tax_included=record.tax_included,
            source_url=record.source_url,
            captured_at_utc=record.captured_at_utc,
            record_id=f"lambda:{record.instance_type}:{index}",
        )
        for index, record in enumerate(catalog.records)
    ]
    return make_price_snapshot(
        provider="lambda",
        source_path=source_path,
        source_type=PriceSourceType.MANUAL_HTML,
        records=records,
        source_url=catalog.source_url,
        captured_at_utc=catalog.captured_at_utc,
        notes=(
            "Operator-provided Lambda public product catalog snapshot; "
            "not live availability evidence."
        ),
        is_sample_data=False,
    )


def import_catalog_price_snapshot_from_html(
    *,
    input_path: str | Path,
    source_url: str,
    output_path: str | Path,
    captured_at_utc: str | None = None,
) -> PriceSnapshot:
    catalog = import_lambda_product_catalog_html(
        input_path,
        source_url=source_url,
        captured_at_utc=captured_at_utc,
    )
    snapshot = price_snapshot_from_product_catalog(catalog, source_path=input_path)
    write_price_snapshot(output_path, snapshot)
    return snapshot


def import_manual_price_snapshot_from_json(
    *,
    input_path: str | Path,
    output_path: str | Path,
    source_url: str | None = None,
    captured_at_utc: str | None = None,
) -> PriceSnapshot:
    catalog = import_lambda_product_catalog_json(
        input_path,
        source_url=source_url,
        captured_at_utc=captured_at_utc,
    )
    snapshot = price_snapshot_from_product_catalog(catalog, source_path=input_path)
    write_price_snapshot(output_path, snapshot)
    return snapshot
