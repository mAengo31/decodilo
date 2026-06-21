"""M037 endpoint confidence decision."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.endpoint_behavior_evidence import (
    LambdaEndpointBehaviorEvidence,
    load_lambda_endpoint_behavior_evidence,
)
from decodilo.lambda_cloud.endpoint_confidence_upgrade import (
    LambdaEndpointConfidenceUpgradeReport,
    load_lambda_endpoint_confidence_upgrade_report,
)
from decodilo.lambda_cloud.support_confirmation_validator import (
    LambdaSupportConfirmationValidationReport,
    load_lambda_support_confirmation_validation_report,
)

LambdaEndpointConfidenceDecisionStatus = Literal[
    "endpoint_confidence_high",
    "endpoint_confidence_medium_accepted",
    "endpoint_confidence_insufficient",
    "endpoint_behavior_contradicts_current_implementation",
    "needs_more_support_evidence",
]


class LambdaEndpointConfidenceDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    status: LambdaEndpointConfidenceDecisionStatus
    confidence: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaEndpointConfidenceDecision:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("endpoint confidence decision cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_endpoint_confidence_decision(
    *,
    validation: LambdaSupportConfirmationValidationReport | None = None,
    endpoint_confidence_upgrade: LambdaEndpointConfidenceUpgradeReport | None = None,
    endpoint_behavior: LambdaEndpointBehaviorEvidence | None = None,
    operator_accepts_medium: bool = False,
) -> LambdaEndpointConfidenceDecision:
    if validation is None or endpoint_confidence_upgrade is None:
        return LambdaEndpointConfidenceDecision(
            status="needs_more_support_evidence",
            confidence="unknown",
            blockers=["support_endpoint_confidence_evidence_missing"],
        )
    blockers = [*validation.blockers, *endpoint_confidence_upgrade.blockers]
    if endpoint_behavior is not None and _contradicts_current_implementation(endpoint_behavior):
        return LambdaEndpointConfidenceDecision(
            status="endpoint_behavior_contradicts_current_implementation",
            confidence=endpoint_confidence_upgrade.upgraded_confidence,
            blockers=["endpoint_behavior_contradicts_current_implementation"],
        )
    if endpoint_confidence_upgrade.upgrade_passed:
        status: LambdaEndpointConfidenceDecisionStatus = "endpoint_confidence_high"
    elif operator_accepts_medium and validation.validation_passed:
        status = "endpoint_confidence_medium_accepted"
    elif validation.validation_passed:
        status = "endpoint_confidence_insufficient"
        blockers.append("endpoint_confidence_not_high")
    else:
        status = "needs_more_support_evidence"
    return LambdaEndpointConfidenceDecision(
        status=status,
        confidence=endpoint_confidence_upgrade.upgraded_confidence,
        blockers=sorted(set(blockers)),
        warnings=[
            "endpoint confidence decision is future-review only",
            *validation.warnings,
            *endpoint_confidence_upgrade.warnings,
        ],
    )


def build_lambda_endpoint_confidence_decision_from_paths(
    *,
    validation: str | Path | None = None,
    endpoint_confidence_upgrade: str | Path | None = None,
    endpoint_behavior: str | Path | None = None,
    operator_accepts_medium: bool = False,
) -> LambdaEndpointConfidenceDecision:
    return build_lambda_endpoint_confidence_decision(
        validation=None
        if validation is None
        else load_lambda_support_confirmation_validation_report(validation),
        endpoint_confidence_upgrade=None
        if endpoint_confidence_upgrade is None
        else load_lambda_endpoint_confidence_upgrade_report(endpoint_confidence_upgrade),
        endpoint_behavior=None
        if endpoint_behavior is None
        else load_lambda_endpoint_behavior_evidence(endpoint_behavior),
        operator_accepts_medium=operator_accepts_medium,
    )


def _contradicts_current_implementation(
    endpoint_behavior: LambdaEndpointBehaviorEvidence,
) -> bool:
    return not (
        endpoint_behavior.launch_method == "POST"
        and endpoint_behavior.launch_path_template == "/instance-operations/launch"
        and endpoint_behavior.terminate_method == "POST"
        and endpoint_behavior.terminate_path_template == "/instance-operations/terminate"
    )


def load_lambda_endpoint_confidence_decision(
    path: str | Path,
) -> LambdaEndpointConfidenceDecision:
    return LambdaEndpointConfidenceDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_endpoint_confidence_decision(
    path: str | Path,
    decision: LambdaEndpointConfidenceDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(decision.to_json(), encoding="utf-8")
