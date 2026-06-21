"""Operator confirmation for M033 endpoint specs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_endpoint_verification import (
    LambdaEndpointVerificationReport,
    load_lambda_endpoint_verification_report,
)

LambdaEndpointSpecOperatorConfirmationStatus = Literal[
    "not_provided",
    "confirmed_high_confidence",
    "confirmed_medium_confidence_accepted",
    "rejected",
]


class LambdaEndpointSpecOperatorConfirmation(BaseModel):
    model_config = ConfigDict(frozen=True)

    confirmation_id: str = "lambda-m033-endpoint-spec-operator-confirmation"
    operator_name: str | None = None
    confirmation_time_utc: str | None = None
    launch_operation: str = "launch_one_instance"
    launch_method: str
    launch_path_template: str
    terminate_operation: str = "terminate_owned_instance"
    terminate_method: str
    terminate_path_template: str
    source_url: str | None = None
    operator_confirms_launch_endpoint: bool = False
    operator_confirms_terminate_endpoint: bool = False
    operator_accepts_medium_confidence: bool = False
    notes: str | None = None
    confirmation_status: LambdaEndpointSpecOperatorConfirmationStatus = "not_provided"
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaEndpointSpecOperatorConfirmation:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("endpoint confirmation cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaEndpointSpecOperatorConfirmationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    confirmation: LambdaEndpointSpecOperatorConfirmation
    endpoint_spec_confidence: str
    confirmation_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaEndpointSpecOperatorConfirmationReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("endpoint confirmation report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_endpoint_spec_operator_confirmation(
    *,
    endpoint_verification: LambdaEndpointVerificationReport,
    operator_confirms_launch_endpoint: bool = False,
    operator_confirms_terminate_endpoint: bool = False,
    operator_accepts_medium_confidence: bool = False,
    operator_name: str | None = None,
    confirmation_time_utc: str | None = None,
    notes: str | None = None,
) -> LambdaEndpointSpecOperatorConfirmationReport:
    launch = _spec_for(endpoint_verification, "launch_one_instance")
    terminate = _spec_for(endpoint_verification, "terminate_owned_instance")
    blockers: list[str] = []
    warnings: list[str] = []
    if launch is None:
        blockers.append("launch_endpoint_spec_missing")
    if terminate is None:
        blockers.append("terminate_endpoint_spec_missing")
    if not endpoint_verification.endpoint_verification_passed:
        blockers.extend(endpoint_verification.blockers)
    if not operator_confirms_launch_endpoint:
        blockers.append("operator_launch_endpoint_confirmation_missing")
    if not operator_confirms_terminate_endpoint:
        blockers.append("operator_terminate_endpoint_confirmation_missing")
    if endpoint_verification.confidence == "medium" and not operator_accepts_medium_confidence:
        blockers.append("operator_medium_confidence_acceptance_missing")
    if endpoint_verification.confidence in {"unknown", "low"}:
        blockers.append("endpoint_spec_confidence_too_low")
    if endpoint_verification.confidence == "medium":
        warnings.append("operator accepted medium confidence endpoint spec for future review")
    if blockers:
        status: LambdaEndpointSpecOperatorConfirmationStatus = (
            "not_provided"
            if not operator_confirms_launch_endpoint
            and not operator_confirms_terminate_endpoint
            else "rejected"
        )
    elif endpoint_verification.confidence == "high":
        status = "confirmed_high_confidence"
    else:
        status = "confirmed_medium_confidence_accepted"
    confirmation = LambdaEndpointSpecOperatorConfirmation(
        operator_name=operator_name,
        confirmation_time_utc=confirmation_time_utc,
        launch_method="" if launch is None else launch.method,
        launch_path_template="" if launch is None else launch.path_template,
        terminate_method="" if terminate is None else terminate.method,
        terminate_path_template="" if terminate is None else terminate.path_template,
        source_url=(launch.source_url if launch is not None else None)
        or (terminate.source_url if terminate is not None else None),
        operator_confirms_launch_endpoint=operator_confirms_launch_endpoint,
        operator_confirms_terminate_endpoint=operator_confirms_terminate_endpoint,
        operator_accepts_medium_confidence=operator_accepts_medium_confidence,
        notes=notes,
        confirmation_status=status,
    )
    return LambdaEndpointSpecOperatorConfirmationReport(
        confirmation=confirmation,
        endpoint_spec_confidence=endpoint_verification.confidence,
        confirmation_passed=not blockers,
        blockers=blockers,
        warnings=warnings,
    )


def build_lambda_endpoint_spec_operator_confirmation_from_path(
    *,
    endpoint_spec: str | Path,
    accept_medium_confidence: bool = False,
    operator_name: str | None = None,
    confirmation_time_utc: str | None = None,
    notes: str | None = None,
) -> LambdaEndpointSpecOperatorConfirmationReport:
    return build_lambda_endpoint_spec_operator_confirmation(
        endpoint_verification=load_lambda_endpoint_verification_report(endpoint_spec),
        operator_confirms_launch_endpoint=True,
        operator_confirms_terminate_endpoint=True,
        operator_accepts_medium_confidence=accept_medium_confidence,
        operator_name=operator_name,
        confirmation_time_utc=confirmation_time_utc,
        notes=notes,
    )


def _spec_for(report: LambdaEndpointVerificationReport, operation: str):
    for spec in report.endpoint_specs:
        if spec.operation == operation:
            return spec
    return None


def load_lambda_endpoint_spec_operator_confirmation(
    path: str | Path,
) -> LambdaEndpointSpecOperatorConfirmationReport:
    return LambdaEndpointSpecOperatorConfirmationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_endpoint_spec_operator_confirmation(
    path: str | Path,
    report: LambdaEndpointSpecOperatorConfirmationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
