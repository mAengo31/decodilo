"""Auditable live-region selection for Lambda lifecycle smoke launches."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_instance_type_parser import (
    build_lambda_live_instance_type_parser_from_path,
    load_lambda_live_instance_type_parser,
)


class LambdaLiveRegionSelectionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    candidate: str
    live_regions: list[str] = Field(default_factory=list)
    selected_region: str | None = None
    selection_source: Literal[
        "operator_preference",
        "prior_successful_region",
        "deterministic_live_region",
        "none",
    ] = "none"
    selection_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_read_only(self) -> LambdaLiveRegionSelectionReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("live region selection cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaLiveRegionSelection = LambdaLiveRegionSelectionReport


def build_lambda_live_region_selection_from_paths(
    *,
    instance_types: str | Path,
    candidate: str,
    preferred_region: str | None = None,
    prior_successful_region: str | None = None,
) -> LambdaLiveRegionSelectionReport:
    path = Path(instance_types)
    try:
        parsed = load_lambda_live_instance_type_parser(path)
    except Exception:
        parsed = build_lambda_live_instance_type_parser_from_path(path)
    return build_lambda_live_region_selection(
        live_regions=[
            region
            for record in parsed.parsed_instance_types
            if record.instance_type_name == candidate
            for region in record.available_regions
        ],
        candidate=candidate,
        preferred_region=preferred_region,
        prior_successful_region=prior_successful_region,
    )


def build_lambda_live_region_selection(
    *,
    live_regions: list[str],
    candidate: str,
    preferred_region: str | None = None,
    prior_successful_region: str | None = None,
) -> LambdaLiveRegionSelectionReport:
    blockers: list[str] = []
    warnings = ["live region selection is read-only and does not authorize launch"]
    unique_regions = sorted(set(live_regions))
    selected: str | None = None
    source: Literal[
        "operator_preference",
        "prior_successful_region",
        "deterministic_live_region",
        "none",
    ] = "none"
    if not unique_regions:
        blockers.append("candidate_has_no_live_available_regions")
    elif preferred_region is not None:
        if preferred_region in unique_regions:
            selected = preferred_region
            source = "operator_preference"
        else:
            blockers.append("preferred_region_not_live_available")
    elif prior_successful_region is not None and prior_successful_region in unique_regions:
        selected = prior_successful_region
        source = "prior_successful_region"
    elif unique_regions:
        selected = unique_regions[0]
        source = "deterministic_live_region"
    return LambdaLiveRegionSelectionReport(
        candidate=candidate,
        live_regions=unique_regions,
        selected_region=selected,
        selection_source=source,
        selection_passed=selected is not None and not blockers,
        blockers=blockers,
        warnings=warnings,
    )


def load_lambda_live_region_selection(path: str | Path) -> LambdaLiveRegionSelectionReport:
    return LambdaLiveRegionSelectionReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_live_region_selection(
    path: str | Path,
    report: LambdaLiveRegionSelectionReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
