"""Resolve stale Lambda catalog shape aliases to canonical live IDs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_instance_type_parser import (
    build_lambda_live_instance_type_parser_from_path,
    load_lambda_live_instance_type_parser,
)

KNOWN_ALIASES: dict[str, str] = {
    "gpu_8x_a100_sxm_80gb": "gpu_8x_a100_80gb_sxm4",
}


class LambdaLiveShapeAliasResolutionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    requested_shape: str
    canonical_live_id: str | None = None
    alias_status: Literal["exact_match", "alias_matched", "unknown_alias", "not_in_live_catalog"]
    source_backed: bool = False
    launch_artifact_shape: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_read_only(self) -> LambdaLiveShapeAliasResolutionReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("live shape alias resolution cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaLiveShapeAliasResolution = LambdaLiveShapeAliasResolutionReport


def build_lambda_live_shape_alias_resolution_from_paths(
    *,
    instance_types: str | Path,
    requested_shape: str,
) -> LambdaLiveShapeAliasResolutionReport:
    path = Path(instance_types)
    try:
        parsed = load_lambda_live_instance_type_parser(path)
    except Exception:
        parsed = build_lambda_live_instance_type_parser_from_path(path)
    live_ids = {record.instance_type_name for record in parsed.parsed_instance_types}
    return build_lambda_live_shape_alias_resolution(
        requested_shape=requested_shape,
        live_ids=live_ids,
    )


def build_lambda_live_shape_alias_resolution(
    *,
    requested_shape: str,
    live_ids: set[str],
) -> LambdaLiveShapeAliasResolutionReport:
    warnings = ["alias resolution is read-only and does not authorize launch"]
    if requested_shape in live_ids:
        return LambdaLiveShapeAliasResolutionReport(
            requested_shape=requested_shape,
            canonical_live_id=requested_shape,
            alias_status="exact_match",
            source_backed=True,
            launch_artifact_shape=requested_shape,
            warnings=warnings,
        )
    canonical = KNOWN_ALIASES.get(requested_shape)
    if canonical is not None and canonical in live_ids:
        return LambdaLiveShapeAliasResolutionReport(
            requested_shape=requested_shape,
            canonical_live_id=canonical,
            alias_status="alias_matched",
            source_backed=True,
            launch_artifact_shape=canonical,
            warnings=[
                *warnings,
                "stale shape alias resolved to canonical live Lambda instance type",
            ],
        )
    return LambdaLiveShapeAliasResolutionReport(
        requested_shape=requested_shape,
        canonical_live_id=canonical,
        alias_status="unknown_alias" if canonical is None else "not_in_live_catalog",
        source_backed=False,
        launch_artifact_shape=None,
        blockers=["shape_alias_not_source_backed_by_live_catalog"],
        warnings=warnings,
    )


def load_lambda_live_shape_alias_resolution(
    path: str | Path,
) -> LambdaLiveShapeAliasResolutionReport:
    return LambdaLiveShapeAliasResolutionReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_live_shape_alias_resolution(
    path: str | Path,
    report: LambdaLiveShapeAliasResolutionReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
