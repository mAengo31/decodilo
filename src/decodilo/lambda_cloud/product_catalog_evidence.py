"""Lambda public product-catalog evidence import helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.shape_evidence import source_hash_for_file
from decodilo.pricing.provenance import utc_now_iso

_MONEY_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


class LambdaProductCatalogRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str = "lambda"
    product_family: str = "on_demand_instance"
    instance_type: str
    gpu_type: str
    gpus_per_instance: int = Field(gt=0)
    gpu_memory_gb: float | None = None
    price_per_gpu_hour: float = Field(ge=0)
    price_per_instance_hour: float = Field(ge=0)
    vcpus: int | None = Field(default=None, ge=0)
    ram_gib: float | None = Field(default=None, ge=0)
    storage: str | None = None
    source_url: str
    captured_at_utc: str
    source_hash: str
    tax_included: bool = False
    is_sample_data: bool = False
    limitations: list[str] = Field(default_factory=list)


class LambdaProductCatalogEvidenceReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    source_url: str
    captured_at_utc: str
    source_hash: str
    records: list[LambdaProductCatalogRecord]
    is_sample_data: bool = False
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def import_lambda_product_catalog_html(
    path: str | Path,
    *,
    source_url: str,
    captured_at_utc: str | None = None,
) -> LambdaProductCatalogEvidenceReport:
    source = Path(path)
    captured = captured_at_utc or _timestamp_from_html(source) or utc_now_iso()
    source_hash = source_hash_for_file(source)
    soup = BeautifulSoup(source.read_text(encoding="utf-8"), "html.parser")
    records: list[LambdaProductCatalogRecord] = []
    for table in soup.find_all("table"):
        headers = [cell.get_text(" ", strip=True).lower() for cell in table.find_all("th")]
        if not headers or "gpu type" not in headers:
            continue
        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
            if not cells:
                continue
            values = dict(zip(headers, cells, strict=False))
            if not values.get("gpu type"):
                continue
            record = _record_from_mapping(
                values,
                source_url=source_url,
                captured_at_utc=captured,
                source_hash=source_hash,
            )
            records.append(record)
    if not records:
        raise ValueError(f"no Lambda product catalog records found in {source}")
    return LambdaProductCatalogEvidenceReport(
        source_url=source_url,
        captured_at_utc=captured,
        source_hash=source_hash,
        records=records,
        warnings=[
            "public product catalog proves advertised product and price, "
            "not live account availability"
        ],
    )


def import_lambda_product_catalog_json(
    path: str | Path,
    *,
    source_url: str | None = None,
    captured_at_utc: str | None = None,
) -> LambdaProductCatalogEvidenceReport:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    source_hash = source_hash_for_file(source)
    effective_source_url = source_url or payload.get("source_url") or str(source)
    captured = captured_at_utc or payload.get("captured_at_utc") or utc_now_iso()
    raw_records = payload.get("records", payload.get("prices", payload))
    if not isinstance(raw_records, list):
        raise ValueError("catalog JSON must contain a record list")
    records = [
        _record_from_mapping(
            record,
            source_url=effective_source_url,
            captured_at_utc=captured,
            source_hash=source_hash,
        )
        for record in raw_records
    ]
    return LambdaProductCatalogEvidenceReport(
        source_url=effective_source_url,
        captured_at_utc=captured,
        source_hash=source_hash,
        records=records,
        warnings=[
            "manual or catalog JSON proves planning evidence only, not live availability"
        ],
    )


def _timestamp_from_html(path: Path) -> str | None:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    meta = soup.find("meta", attrs={"name": "snapshot-timestamp"})
    if meta and meta.get("content"):
        return str(meta["content"])
    return None


def _record_from_mapping(
    values: dict[str, Any],
    *,
    source_url: str,
    captured_at_utc: str,
    source_hash: str,
) -> LambdaProductCatalogRecord:
    normalized = {str(key).lower().strip(): value for key, value in values.items()}
    gpu_type = str(normalized.get("gpu type") or normalized.get("gpu_type") or "")
    if not gpu_type:
        raise ValueError("catalog record missing gpu_type")
    gpus = _parse_int(
        normalized.get("gpus")
        or normalized.get("gpus per instance")
        or normalized.get("gpus_per_instance")
        or 1
    )
    price_per_gpu = _parse_money(
        normalized.get("price / gpu hour")
        or normalized.get("price per gpu hour")
        or normalized.get("price_per_gpu_hour")
        or 0
    )
    price_per_instance = normalized.get("price / instance hour") or normalized.get(
        "price_per_instance_hour"
    )
    instance_type = str(
        normalized.get("instance type")
        or normalized.get("instance_type")
        or normalized.get("instance")
        or _instance_type_from_gpu(gpu_type, gpus)
    )
    return LambdaProductCatalogRecord(
        instance_type=instance_type,
        gpu_type=gpu_type,
        gpus_per_instance=gpus,
        gpu_memory_gb=_optional_float(
            normalized.get("gpu memory (gb)")
            or normalized.get("gpu_memory_gb")
            or normalized.get("memory gb")
        ),
        price_per_gpu_hour=price_per_gpu,
        price_per_instance_hour=(
            _parse_money(price_per_instance)
            if price_per_instance is not None
            else round(price_per_gpu * gpus, 8)
        ),
        vcpus=_optional_int(normalized.get("vcpus") or normalized.get("vcpus")),
        ram_gib=_optional_float(normalized.get("ram (gib)") or normalized.get("ram_gib")),
        storage=None if normalized.get("storage") is None else str(normalized.get("storage")),
        source_url=source_url,
        captured_at_utc=captured_at_utc,
        source_hash=source_hash,
        tax_included=str(normalized.get("tax included", "false")).lower() == "true",
        is_sample_data=False,
        limitations=[
            "public catalog price is not proof of live capacity or account availability"
        ],
    )


def _instance_type_from_gpu(gpu_type: str, gpus: int) -> str:
    token = gpu_type.lower().replace(" ", "_").replace("-", "_")
    return f"gpu_{gpus}x_{token}"


def _parse_money(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    match = _MONEY_RE.search(str(value).replace(",", ""))
    if not match:
        raise ValueError(f"could not parse money value: {value!r}")
    return float(match.group(0))


def _parse_int(value: object) -> int:
    if isinstance(value, int):
        return value
    match = _MONEY_RE.search(str(value).replace(",", ""))
    if not match:
        raise ValueError(f"could not parse integer value: {value!r}")
    return int(float(match.group(0)))


def _optional_float(value: object | None) -> float | None:
    if value in {None, ""}:
        return None
    return _parse_money(value)


def _optional_int(value: object | None) -> int | None:
    if value in {None, ""}:
        return None
    return _parse_int(value)


def load_lambda_product_catalog_evidence_report(
    path: str | Path,
) -> LambdaProductCatalogEvidenceReport:
    return LambdaProductCatalogEvidenceReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_product_catalog_evidence_report(
    path: str | Path,
    report: LambdaProductCatalogEvidenceReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
