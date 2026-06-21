"""M036 response-shape evidence for launch and terminate operations."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.endpoint_behavior_evidence import (
    LambdaEndpointBehaviorEvidence,
    load_lambda_endpoint_behavior_evidence,
)


class LambdaResponseShapeEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_expected_status_codes: list[int]
    launch_expected_content_types: list[str]
    launch_response_body_shape: str
    launch_response_instance_id_field: str | None = None
    launch_async_without_id_possible: bool = False
    terminate_expected_status_codes: list[int]
    terminate_response_body_shape: str
    terminate_terminal_states: list[str]
    evidence_confidence: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaResponseShapeEvidence:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("response shape evidence cannot enable launch")
        if not self.launch_response_instance_id_field and not self.launch_async_without_id_possible:
            raise ValueError("launch response needs ID field or async/no-ID semantics")
        if not self.terminate_terminal_states:
            raise ValueError("terminate terminal states required")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_response_shape_evidence(
    endpoint_behavior: LambdaEndpointBehaviorEvidence,
) -> LambdaResponseShapeEvidence:
    blockers = list(endpoint_behavior.blockers)
    return LambdaResponseShapeEvidence(
        launch_expected_status_codes=endpoint_behavior.launch_expected_status_codes,
        launch_expected_content_types=endpoint_behavior.launch_expected_content_types,
        launch_response_body_shape=(
            "JSON object containing instance identifier"
            if endpoint_behavior.launch_response_instance_id_field
            else "accepted/async response may omit instance identifier"
        ),
        launch_response_instance_id_field=(
            endpoint_behavior.launch_response_instance_id_field
        ),
        launch_async_without_id_possible=endpoint_behavior.launch_async_without_id_possible,
        terminate_expected_status_codes=endpoint_behavior.terminate_expected_status_codes,
        terminate_response_body_shape="JSON/empty success body followed by read-only verification",
        terminate_terminal_states=endpoint_behavior.terminate_terminal_states,
        evidence_confidence=endpoint_behavior.evidence_confidence,
        blockers=blockers,
        warnings=endpoint_behavior.warnings,
    )


def build_lambda_response_shape_evidence_from_path(
    endpoint_behavior: str | Path,
) -> LambdaResponseShapeEvidence:
    return build_lambda_response_shape_evidence(
        load_lambda_endpoint_behavior_evidence(endpoint_behavior)
    )


def load_lambda_response_shape_evidence(path: str | Path) -> LambdaResponseShapeEvidence:
    return LambdaResponseShapeEvidence.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_response_shape_evidence(
    path: str | Path,
    report: LambdaResponseShapeEvidence,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")

