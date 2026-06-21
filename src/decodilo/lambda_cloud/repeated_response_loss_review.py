"""Review repeated Lambda launch response loss before future launch attempts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_endpoint_diagnostics import (
    LambdaLaunchEndpointDiagnosticsReport,
    load_lambda_launch_endpoint_diagnostics,
)
from decodilo.lambda_cloud.launch_response_loss_root_cause import (
    LambdaLaunchResponseLossRootCauseReport,
    evaluate_lambda_launch_response_loss_root_cause,
)
from decodilo.lambda_cloud.launch_transport_diagnostics import (
    LambdaLaunchTransportDiagnosticsReport,
    load_lambda_launch_transport_diagnostics,
)
from decodilo.lambda_cloud.m029_incident_closeout import (
    LambdaM029IncidentCloseoutReport,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report, load_lambda_m029_report
from decodilo.lambda_cloud.m031_incident_closeout import LambdaM031IncidentCloseoutReport

LambdaRepeatedResponseLossReviewStatus = Literal[
    "not_required",
    "blocked",
    "mitigation_required",
    "mitigation_accepted",
]


class LambdaRepeatedResponseLossReviewReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    repeated_response_loss_detected: bool
    attempts_analyzed: int
    response_loss_count: int
    successful_launch_response_count: int
    m029_incident_closed: bool
    m031_incident_closed: bool
    root_cause: LambdaLaunchResponseLossRootCauseReport
    review_status: LambdaRepeatedResponseLossReviewStatus
    mitigation_accepted: bool = False
    future_launch_blocked: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaRepeatedResponseLossReviewReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("repeated response-loss review cannot enable launch")
        if self.repeated_response_loss_detected and not self.mitigation_accepted:
            if not self.future_launch_blocked:
                raise ValueError("unmitigated repeated response loss must block launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_repeated_response_loss_review(
    *,
    m029c_report: LambdaM029Report,
    m031_report: LambdaM029Report,
    m029e_closeout: LambdaM029IncidentCloseoutReport,
    m031_closeout: LambdaM031IncidentCloseoutReport,
    transport_diagnostics: LambdaLaunchTransportDiagnosticsReport | None = None,
    endpoint_diagnostics: LambdaLaunchEndpointDiagnosticsReport | None = None,
    mitigation_accepted: bool = False,
) -> LambdaRepeatedResponseLossReviewReport:
    attempts = [m029c_report, m031_report]
    root = evaluate_lambda_launch_response_loss_root_cause(
        attempts=attempts,
        transport_diagnostics=transport_diagnostics,
        endpoint_diagnostics=endpoint_diagnostics,
        mitigation_accepted=mitigation_accepted,
    )
    blockers: list[str] = []
    if not m029e_closeout.closeout_succeeded:
        blockers.append("m029_incident_not_closed")
    if not m031_closeout.closeout_succeeded:
        blockers.append("m031_incident_not_closed")
    if blockers:
        status: LambdaRepeatedResponseLossReviewStatus = "blocked"
    elif not root.repeated_response_loss_detected:
        status = "not_required"
    elif mitigation_accepted:
        status = "mitigation_accepted"
    else:
        status = "mitigation_required"
    review_blockers = list(blockers)
    if root.repeated_response_loss_detected and not mitigation_accepted:
        review_blockers.append("repeated_response_loss_mitigation_required")
    future_launch_blocked = bool(review_blockers)
    return LambdaRepeatedResponseLossReviewReport(
        repeated_response_loss_detected=root.repeated_response_loss_detected,
        attempts_analyzed=root.attempts_analyzed,
        response_loss_count=root.response_loss_count,
        successful_launch_response_count=root.successful_launch_response_count,
        m029_incident_closed=m029e_closeout.closeout_succeeded,
        m031_incident_closed=m031_closeout.closeout_succeeded,
        root_cause=root,
        review_status=status,
        mitigation_accepted=mitigation_accepted,
        future_launch_blocked=future_launch_blocked,
        blockers=review_blockers,
        warnings=root.warnings,
    )


def build_lambda_repeated_response_loss_review_from_paths(
    *,
    m029c_report: str | Path,
    m031_report: str | Path,
    m029e_closeout: str | Path,
    m031_closeout: str | Path,
    transport_diagnostics: str | Path | None = None,
    endpoint_diagnostics: str | Path | None = None,
    mitigation_accepted: bool = False,
) -> LambdaRepeatedResponseLossReviewReport:
    return build_lambda_repeated_response_loss_review(
        m029c_report=load_lambda_m029_report(m029c_report),
        m031_report=load_lambda_m029_report(m031_report),
        m029e_closeout=LambdaM029IncidentCloseoutReport.model_validate_json(
            Path(m029e_closeout).read_text(encoding="utf-8")
        ),
        m031_closeout=LambdaM031IncidentCloseoutReport.model_validate_json(
            Path(m031_closeout).read_text(encoding="utf-8")
        ),
        transport_diagnostics=None
        if transport_diagnostics is None
        else load_lambda_launch_transport_diagnostics(transport_diagnostics),
        endpoint_diagnostics=None
        if endpoint_diagnostics is None
        else load_lambda_launch_endpoint_diagnostics(endpoint_diagnostics),
        mitigation_accepted=mitigation_accepted,
    )


def load_lambda_repeated_response_loss_review(
    path: str | Path,
) -> LambdaRepeatedResponseLossReviewReport:
    return LambdaRepeatedResponseLossReviewReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_repeated_response_loss_review(
    path: str | Path,
    report: LambdaRepeatedResponseLossReviewReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
