"""Join live Lambda shape IDs to non-sample price snapshot records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_shape_alias_resolution import (
    KNOWN_ALIASES,
    load_lambda_live_shape_alias_resolution,
)
from decodilo.pricing.snapshots import load_price_snapshot


class LambdaLiveShapePriceJoinReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    live_instance_type_name: str
    catalog_price_record_id: str | None = None
    price_per_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    join_status: Literal["matched", "alias_matched", "missing_price", "ambiguous"]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_read_only(self) -> LambdaLiveShapePriceJoinReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("live shape price join cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_live_shape_price_join_from_paths(
    *,
    price_snapshot: str | Path,
    live_instance_type_name: str,
    alias_resolution: str | Path | None = None,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaLiveShapePriceJoinReport:
    snapshot = load_price_snapshot(price_snapshot)
    alias = (
        None
        if alias_resolution is None or not Path(alias_resolution).exists()
        else load_lambda_live_shape_alias_resolution(alias_resolution)
    )
    aliases = {stale: canonical for stale, canonical in KNOWN_ALIASES.items()}
    if alias is not None and alias.canonical_live_id:
        aliases[alias.requested_shape] = alias.canonical_live_id
    return build_lambda_live_shape_price_join(
        records=snapshot.records,
        is_sample_data=snapshot.is_sample_data,
        live_instance_type_name=live_instance_type_name,
        aliases=aliases,
        safety_buffer_multiplier=safety_buffer_multiplier,
    )


def build_lambda_live_shape_price_join(
    *,
    records,
    is_sample_data: bool,
    live_instance_type_name: str,
    aliases: dict[str, str] | None = None,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaLiveShapePriceJoinReport:
    blockers: list[str] = []
    warnings = ["price join is read-only and does not authorize launch"]
    if is_sample_data:
        blockers.append("sample_price_snapshot_not_allowed")
    exact = [
        record
        for record in records
        if record.provider == "lambda" and record.instance_type == live_instance_type_name
    ]
    alias_matches = []
    for stale, canonical in (aliases or {}).items():
        if canonical == live_instance_type_name:
            alias_matches.extend(
                record
                for record in records
                if record.provider == "lambda" and record.instance_type == stale
            )
    matches = exact or alias_matches
    if len(matches) > 1:
        blockers.append("ambiguous_price_records")
        status: Literal["matched", "alias_matched", "missing_price", "ambiguous"] = "ambiguous"
        record = None
    elif not matches:
        blockers.append("price_record_missing_for_live_shape")
        status = "missing_price"
        record = None
    else:
        record = matches[0]
        status = "matched" if exact else "alias_matched"
    estimate = None if record is None else round(record.price_per_instance_hour * 0.5, 8)
    buffered = None if estimate is None else round(estimate * safety_buffer_multiplier, 8)
    return LambdaLiveShapePriceJoinReport(
        live_instance_type_name=live_instance_type_name,
        catalog_price_record_id=None if record is None else record.record_id,
        price_per_hour=None if record is None else record.price_per_instance_hour,
        estimated_30min_cost=estimate,
        buffered_estimated_30min_cost=buffered,
        join_status=status,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def load_lambda_live_shape_price_join(path: str | Path) -> LambdaLiveShapePriceJoinReport:
    return LambdaLiveShapePriceJoinReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_live_shape_price_join(
    path: str | Path,
    report: LambdaLiveShapePriceJoinReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
