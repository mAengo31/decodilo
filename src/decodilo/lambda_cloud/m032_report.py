"""Combined M032 repeated response-loss mitigation report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.future_launch_hold_release import (
    LambdaFutureLaunchHoldReleaseReport,
    load_lambda_future_launch_hold_release,
)
from decodilo.lambda_cloud.launch_endpoint_verification import (
    LambdaEndpointVerificationReport,
    load_lambda_endpoint_verification_report,
)
from decodilo.lambda_cloud.response_loss_mitigation_acceptance import (
    LambdaResponseLossMitigationAcceptanceReport,
    load_lambda_response_loss_mitigation_acceptance,
)
from decodilo.lambda_cloud.response_loss_regression_harness import (
    LambdaResponseLossRegressionReport,
    load_lambda_response_loss_regression_report,
)


class LambdaM032Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    response_capture_implemented: bool
    diagnostics_implemented: bool
    endpoint_spec_status: str
    regression_harness_passed: bool
    mitigation_accepted: bool
    future_launch_hold_released_for_review: bool
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM032Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M032 report cannot enable launch or record billable action")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m032_report(
    *,
    endpoint_verification: LambdaEndpointVerificationReport,
    regression_report: LambdaResponseLossRegressionReport,
    mitigation_acceptance: LambdaResponseLossMitigationAcceptanceReport,
    hold_release: LambdaFutureLaunchHoldReleaseReport | None = None,
) -> LambdaM032Report:
    errors: list[str] = []
    if not endpoint_verification.endpoint_verification_passed:
        errors.extend(endpoint_verification.blockers)
    if not regression_report.regression_harness_passed:
        errors.extend(regression_report.errors)
    if not mitigation_acceptance.mitigation_accepted:
        errors.extend(mitigation_acceptance.blockers)
    return LambdaM032Report(
        response_capture_implemented=mitigation_acceptance.response_capture_implemented,
        diagnostics_implemented=True,
        endpoint_spec_status=mitigation_acceptance.endpoint_spec_status,
        regression_harness_passed=regression_report.regression_harness_passed,
        mitigation_accepted=mitigation_acceptance.mitigation_accepted,
        future_launch_hold_released_for_review=bool(
            hold_release and hold_release.hold_released_for_future_review
        ),
        warnings=[
            *endpoint_verification.warnings,
            *regression_report.warnings,
            *mitigation_acceptance.warnings,
            *(hold_release.warnings if hold_release else []),
        ],
        errors=errors,
    )


def build_lambda_m032_report_from_paths(
    *,
    endpoint_spec: str | Path,
    regression_report: str | Path,
    mitigation_acceptance: str | Path,
    hold_release: str | Path | None = None,
) -> LambdaM032Report:
    return build_lambda_m032_report(
        endpoint_verification=load_lambda_endpoint_verification_report(endpoint_spec),
        regression_report=load_lambda_response_loss_regression_report(regression_report),
        mitigation_acceptance=load_lambda_response_loss_mitigation_acceptance(
            mitigation_acceptance
        ),
        hold_release=None
        if hold_release is None
        else load_lambda_future_launch_hold_release(hold_release),
    )


def load_lambda_m032_report(path: str | Path) -> LambdaM032Report:
    return LambdaM032Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m032_report(path: str | Path, report: LambdaM032Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
