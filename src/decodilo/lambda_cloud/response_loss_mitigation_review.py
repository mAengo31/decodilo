"""Response-loss mitigation review for a future second Lambda launch attempt."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m029_incident_report import (
    LambdaM029IncidentReport,
    load_lambda_m029_incident_report,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report, load_lambda_m029_report


class LambdaResponseLossMitigationReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    mitigation_passed: bool
    m029c_incident_closed: bool
    second_idempotency_key_distinct: bool
    pre_launch_discovery_required: bool = True
    deterministic_idempotency_key_required: bool = True
    launch_journal_before_send_required: bool = True
    launch_request_hash_required: bool = True
    planned_shape_region_image_required: bool = True
    automatic_retry_forbidden: bool = True
    post_timeout_discovery_required: bool = True
    candidate_matching_required: bool = True
    owned_termination_only_required: bool = True
    manual_console_review_on_uncertainty_required: bool = True
    missing_mitigations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaResponseLossMitigationReview:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("mitigation review cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_response_loss_mitigation_review(
    *,
    incident: LambdaM029IncidentReport,
    prior_m029_report: LambdaM029Report,
    second_idempotency_key: str = "m031-launch-one-instance",
    prior_idempotency_key: str = "m029-launch-one-instance",
    no_auto_retry: bool = True,
) -> LambdaResponseLossMitigationReview:
    missing: list[str] = []
    incident_closed = incident.incident_status.startswith("closed_")
    if not incident_closed:
        missing.append("m029c_incident_closed")
    if not no_auto_retry:
        missing.append("automatic_retry_forbidden")
    if second_idempotency_key == prior_idempotency_key:
        missing.append("second_idempotency_key_distinct")
    if not prior_m029_report.launch_request_sent:
        missing.append("prior_launch_attempt_reported")
    return LambdaResponseLossMitigationReview(
        mitigation_passed=not missing,
        m029c_incident_closed=incident_closed,
        second_idempotency_key_distinct=second_idempotency_key != prior_idempotency_key,
        automatic_retry_forbidden=no_auto_retry,
        missing_mitigations=missing,
        warnings=[
            "response loss mitigation is review evidence only; M030 cannot launch"
        ],
    )


def build_lambda_response_loss_mitigation_review_from_paths(
    *,
    incident_report: str | Path,
    prior_m029_report: str | Path,
) -> LambdaResponseLossMitigationReview:
    return build_lambda_response_loss_mitigation_review(
        incident=load_lambda_m029_incident_report(incident_report),
        prior_m029_report=load_lambda_m029_report(prior_m029_report),
    )


def load_lambda_response_loss_mitigation_review(
    path: str | Path,
) -> LambdaResponseLossMitigationReview:
    return LambdaResponseLossMitigationReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_response_loss_mitigation_review(
    path: str | Path,
    report: LambdaResponseLossMitigationReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
