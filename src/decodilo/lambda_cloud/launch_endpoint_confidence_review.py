"""M035 endpoint confidence review after repeated response loss."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_attempt_history import (
    LambdaLaunchAttemptHistoryReport,
    load_lambda_launch_attempt_history_report,
)
from decodilo.lambda_cloud.launch_endpoint_spec import LambdaEndpointOperationSpec
from decodilo.lambda_cloud.launch_endpoint_verification import (
    LambdaEndpointVerificationReport,
)

EndpointConfidence = Literal["low", "medium", "high"]


class LambdaLaunchEndpointConfidenceReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    endpoint_confidence_current: EndpointConfidence
    endpoint_confidence_recommended: EndpointConfidence
    launch_method: str | None = None
    launch_path: str | None = None
    terminate_method: str | None = None
    terminate_path: str | None = None
    response_loss_count: int
    repeated_response_loss_detected: bool
    confidence_blockers: list[str] = Field(default_factory=list)
    confidence_warnings: list[str] = Field(default_factory=list)
    support_or_docs_confirmation_required: bool
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLaunchEndpointConfidenceReview:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M035 endpoint confidence review cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_endpoint_confidence_review(
    *,
    endpoint_verification: LambdaEndpointVerificationReport,
    attempt_history: LambdaLaunchAttemptHistoryReport,
    operator_explicitly_accepts_medium_after_three_losses: bool = False,
) -> LambdaLaunchEndpointConfidenceReview:
    specs = {spec.operation: spec for spec in endpoint_verification.endpoint_specs}
    current = _normalize_confidence(endpoint_verification.confidence)
    blockers = list(endpoint_verification.blockers)
    warnings = list(endpoint_verification.warnings)
    support_required = False
    recommended: EndpointConfidence = current
    if current == "medium" and attempt_history.response_loss_count >= 3:
        warnings.append(
            "endpoint confidence is still medium after three response-loss attempts"
        )
        if not operator_explicitly_accepts_medium_after_three_losses:
            support_required = True
            recommended = "high"
            blockers.append("support_or_docs_confirmation_required_after_three_losses")
    if current == "low":
        support_required = True
        recommended = "high"
        blockers.append("endpoint_confidence_low")
    launch = specs.get("launch_one_instance")
    terminate = specs.get("terminate_owned_instance")
    return LambdaLaunchEndpointConfidenceReview(
        endpoint_confidence_current=current,
        endpoint_confidence_recommended=recommended,
        launch_method=None if launch is None else launch.method,
        launch_path=None if launch is None else launch.path_template,
        terminate_method=None if terminate is None else terminate.method,
        terminate_path=None if terminate is None else terminate.path_template,
        response_loss_count=attempt_history.response_loss_count,
        repeated_response_loss_detected=attempt_history.repeated_response_loss_detected,
        confidence_blockers=blockers,
        confidence_warnings=warnings,
        support_or_docs_confirmation_required=support_required,
    )


def build_lambda_launch_endpoint_confidence_review_from_paths(
    *,
    endpoint_spec: str | Path,
    attempt_history: str | Path,
) -> LambdaLaunchEndpointConfidenceReview:
    return build_lambda_launch_endpoint_confidence_review(
        endpoint_verification=_load_endpoint_verification(endpoint_spec),
        attempt_history=load_lambda_launch_attempt_history_report(attempt_history),
    )


def _load_endpoint_verification(path: str | Path) -> LambdaEndpointVerificationReport:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "endpoint_specs" in payload:
        return LambdaEndpointVerificationReport.model_validate(payload)
    if "operation" in payload:
        spec = LambdaEndpointOperationSpec.model_validate(payload)
        return LambdaEndpointVerificationReport(
            endpoint_specs=[spec],
            endpoint_verification_passed=spec.confidence in {"medium", "high"},
            verified_operations=[spec.operation],
            confidence=_normalize_confidence(spec.confidence),
            blockers=[]
            if spec.confidence in {"medium", "high"}
            else ["endpoint_confidence_too_low"],
        )
    raise ValueError("endpoint spec must be an endpoint spec or verification report")


def _normalize_confidence(value: Any) -> EndpointConfidence:
    if value == "high":
        return "high"
    if value == "medium":
        return "medium"
    return "low"


def load_lambda_launch_endpoint_confidence_review(
    path: str | Path,
) -> LambdaLaunchEndpointConfidenceReview:
    return LambdaLaunchEndpointConfidenceReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_launch_endpoint_confidence_review(
    path: str | Path,
    report: LambdaLaunchEndpointConfidenceReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
