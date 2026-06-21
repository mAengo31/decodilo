"""First-class parser for Lambda Cloud live instance-type responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaLiveInstanceTypeRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    instance_type_name: str
    gpu_description: str | None = None
    price_per_hour: float | None = None
    available_regions: list[str] = Field(default_factory=list)
    live_available: bool = False
    source: Literal["live_read_only"] = "live_read_only"
    raw_fields: dict[str, Any] = Field(default_factory=dict)


class LambdaLiveInstanceTypeParserReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    response_shape: Literal["map", "list", "unknown"]
    parsed_instance_types: list[LambdaLiveInstanceTypeRecord] = Field(
        default_factory=list
    )
    parser_status: Literal["parsed", "empty", "unsupported"]
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_read_only(self) -> LambdaLiveInstanceTypeParserReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("live instance-type parser cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def parse_lambda_live_instance_types(payload: Any) -> LambdaLiveInstanceTypeParserReport:
    data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
    records: list[LambdaLiveInstanceTypeRecord] = []
    warnings: list[str] = []
    response_shape: Literal["map", "list", "unknown"] = "unknown"
    if isinstance(data, dict):
        response_shape = "map"
        records = [
            _record_from_map_entry(name, entry)
            for name, entry in sorted(data.items())
            if isinstance(name, str) and isinstance(entry, dict)
        ]
    elif isinstance(data, list):
        response_shape = "list"
        records = [
            record
            for item in data
            if isinstance(item, dict)
            for record in [_record_from_list_item(item)]
            if record is not None
        ]
    else:
        return LambdaLiveInstanceTypeParserReport(
            response_shape=response_shape,
            parser_status="unsupported",
            blockers=["unsupported_instance_types_response_shape"],
        )
    if not records:
        warnings.append("instance-types response parsed but contained no records")
    for record in records:
        if not record.available_regions:
            warnings.append(f"missing_live_regions:{record.instance_type_name}")
    return LambdaLiveInstanceTypeParserReport(
        response_shape=response_shape,
        parsed_instance_types=records,
        parser_status="parsed" if records else "empty",
        warnings=sorted(set(warnings)),
    )


def build_lambda_live_instance_type_parser_from_path(
    instance_types: str | Path,
) -> LambdaLiveInstanceTypeParserReport:
    return parse_lambda_live_instance_types(
        json.loads(Path(instance_types).read_text(encoding="utf-8"))
    )


def _record_from_map_entry(
    name: str,
    entry: dict[str, Any],
) -> LambdaLiveInstanceTypeRecord:
    instance_type = entry.get("instance_type")
    if not isinstance(instance_type, dict):
        instance_type = entry
    regions = _region_names(entry.get("regions_with_capacity_available"))
    return LambdaLiveInstanceTypeRecord(
        instance_type_name=name,
        gpu_description=_string_or_none(instance_type.get("description")),
        price_per_hour=_price_per_hour(instance_type),
        available_regions=regions,
        live_available=bool(regions),
        raw_fields={
            "response_shape": "map",
            "instance_type": instance_type,
        },
    )


def _record_from_list_item(item: dict[str, Any]) -> LambdaLiveInstanceTypeRecord | None:
    nested_instance_type = item.get("instance_type")
    instance_type = nested_instance_type if isinstance(nested_instance_type, dict) else item
    if not isinstance(instance_type, dict):
        return None
    name = (
        item.get("name")
        or item.get("instance_type_name")
        or instance_type.get("name")
        or instance_type.get("instance_type_name")
        or instance_type.get("instance_type_id")
    )
    if not isinstance(name, str) or not name:
        return None
    regions = _region_names(
        item.get("regions_with_capacity_available")
        or item.get("available_regions")
        or instance_type.get("regions")
    )
    return LambdaLiveInstanceTypeRecord(
        instance_type_name=name,
        gpu_description=_string_or_none(
            item.get("description") or instance_type.get("description")
        ),
        price_per_hour=_price_per_hour(instance_type),
        available_regions=regions,
        live_available=bool(regions) or bool(item.get("available")),
        raw_fields={"response_shape": "list", "item": item},
    )


def _price_per_hour(instance_type: dict[str, Any]) -> float | None:
    cents = instance_type.get("price_cents_per_hour")
    if isinstance(cents, (int, float)):
        return float(cents) / 100.0
    if isinstance(cents, str):
        try:
            return float(cents) / 100.0
        except ValueError:
            return None
    for key in ("price_per_hour", "price_per_instance_hour", "hourly_price", "price"):
        value = instance_type.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace("$", "").replace("/hr", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                continue
    return None


def _region_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    regions: list[str] = []
    for item in value:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            regions.append(item["name"])
        elif isinstance(item, str):
            regions.append(item)
    return [region for region in regions if region]


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def load_lambda_live_instance_type_parser(
    path: str | Path,
) -> LambdaLiveInstanceTypeParserReport:
    return LambdaLiveInstanceTypeParserReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_live_instance_type_parser(
    path: str | Path,
    report: LambdaLiveInstanceTypeParserReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
