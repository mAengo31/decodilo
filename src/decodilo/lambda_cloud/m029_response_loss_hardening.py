"""Response-loss hardening policy for future M029 launch attempts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LambdaM029ResponseLossHardeningReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    auto_retry_launch_allowed: bool = False
    provider_metadata_correlation_supported: bool = False
    required_correlation_fields: list[str] = Field(default_factory=list)
    candidate_matching_fields: list[str] = Field(default_factory=list)
    ambiguity_blocks_termination: bool = True
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m029_response_loss_hardening_report(
    *,
    provider_metadata_correlation_supported: bool = False,
) -> LambdaM029ResponseLossHardeningReport:
    limitations: list[str] = []
    if not provider_metadata_correlation_supported:
        limitations.append("provider launch metadata/tags not confirmed for correlation")
    return LambdaM029ResponseLossHardeningReport(
        provider_metadata_correlation_supported=provider_metadata_correlation_supported,
        required_correlation_fields=[
            "client_correlation_id",
            "request_hash",
            "request_sent_timestamp_utc",
            "idempotency_key",
            "planned_shape",
            "planned_region",
            "planned_image",
        ],
        candidate_matching_fields=[
            "shape",
            "region",
            "creation_time_window",
            "status",
            "account_visibility",
        ],
        limitations=limitations,
        warnings=["response loss must not trigger automatic launch retry"],
    )


def candidate_matches_response_loss_policy(
    candidate: dict[str, Any],
    *,
    planned_shape: str,
    planned_region: str,
) -> bool:
    shape = str(candidate.get("instance_type") or candidate.get("shape") or "")
    region = str(candidate.get("region") or "")
    return shape == planned_shape and (not region or region == planned_region)


def write_lambda_m029_response_loss_hardening_report(
    path: str | Path,
    report: LambdaM029ResponseLossHardeningReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
