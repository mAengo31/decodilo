"""Offline regression harness for Lambda launch response-loss scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnosticReport,
    LambdaMutationTransportDiagnostics,
    build_lambda_mutation_transport_diagnostic_report,
)
from decodilo.lambda_cloud.response_loss_fixture_builder import (
    LambdaResponseLossFixtureScenario,
    build_lambda_response_loss_diagnostic_fixture,
)

DEFAULT_RESPONSE_LOSS_SCENARIOS: tuple[LambdaResponseLossFixtureScenario, ...] = (
    "launch_timeout_before_status",
    "launch_status_200_empty_body",
    "launch_status_200_non_json_body",
    "launch_status_202_json_unexpected_schema",
    "launch_status_4xx_json_error",
    "launch_status_5xx_non_json",
    "terminate_timeout_before_status",
    "terminate_status_200_empty_body",
    "terminate_status_202_json_unexpected_schema",
)

LambdaOwnedResourceReconciliationBehavior = Literal[
    "no_candidate_manual_review",
    "status_error_no_retry",
    "schema_failure_manual_review",
]


class LambdaResponseLossScenarioResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario: LambdaResponseLossFixtureScenario
    operation: str
    expected_classification: str
    observed_classification: str
    diagnostic_report: LambdaMutationTransportDiagnosticReport
    no_automatic_relaunch: bool = True
    no_unowned_termination: bool = True
    manual_review_required: bool
    owned_resource_reconciliation_behavior: LambdaOwnedResourceReconciliationBehavior
    passed: bool
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)


class LambdaResponseLossRegressionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    scenarios_requested: list[str]
    scenarios_completed: list[str]
    all_scenarios_covered: bool
    regression_harness_passed: bool
    scenario_results: list[LambdaResponseLossScenarioResult]
    no_real_lambda_call: bool = True
    no_real_mutation: bool = True
    no_automatic_relaunch: bool = True
    no_unowned_termination: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaResponseLossRegressionReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("response-loss regression harness cannot enable launch")
        if not self.no_real_lambda_call or not self.no_real_mutation:
            raise ValueError("response-loss regression harness is offline only")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_lambda_response_loss_regression_harness(
    scenarios: list[LambdaResponseLossFixtureScenario] | None = None,
) -> LambdaResponseLossRegressionReport:
    requested = scenarios or list(DEFAULT_RESPONSE_LOSS_SCENARIOS)
    results: list[LambdaResponseLossScenarioResult] = []
    for scenario in requested:
        fixture = build_lambda_response_loss_diagnostic_fixture(scenario)
        capture = fixture.response_capture
        diagnostics = LambdaMutationTransportDiagnostics(
            operation=fixture.operation,
            stages=_stages_for_classification(capture.classification),
            response_capture=capture,
            real_lambda_api_used=False,
        )
        diagnostic_report = build_lambda_mutation_transport_diagnostic_report([diagnostics])
        expected = _expected_classification(scenario)
        manual_review = capture.classification in {
            "timeout",
            "success_empty_body",
            "success_non_json",
            "schema_validation_failure",
            "http_error_json",
            "http_error_non_json",
        }
        results.append(
            LambdaResponseLossScenarioResult(
                scenario=scenario,
                operation=fixture.operation,
                expected_classification=expected,
                observed_classification=capture.classification,
                diagnostic_report=diagnostic_report,
                manual_review_required=manual_review,
                owned_resource_reconciliation_behavior=_reconciliation_behavior(
                    capture.classification
                ),
                passed=bool(
                    capture.classification == expected
                    and diagnostic_report.status_captured_before_parse
                    and diagnostic_report.no_secret_leakage
                ),
                warnings=fixture.warnings,
            )
        )
    completed = [result.scenario for result in results]
    errors: list[str] = []
    if set(completed) != set(DEFAULT_RESPONSE_LOSS_SCENARIOS):
        errors.append("not all required response-loss scenarios were covered")
    if any(not result.passed for result in results):
        errors.append("one or more response-loss scenarios failed")
    return LambdaResponseLossRegressionReport(
        scenarios_requested=list(requested),
        scenarios_completed=completed,
        all_scenarios_covered=set(completed) == set(DEFAULT_RESPONSE_LOSS_SCENARIOS),
        regression_harness_passed=not errors,
        scenario_results=results,
        errors=errors,
    )


def _expected_classification(scenario: str) -> str:
    if scenario.endswith("timeout_before_status"):
        return "timeout"
    if scenario.endswith("200_empty_body"):
        return "success_empty_body"
    if scenario.endswith("200_non_json_body"):
        return "success_non_json"
    if scenario.endswith("202_json_unexpected_schema"):
        return "schema_validation_failure"
    if scenario.endswith("4xx_json_error"):
        return "http_error_json"
    if scenario.endswith("5xx_non_json"):
        return "http_error_non_json"
    raise ValueError(f"unsupported response-loss scenario: {scenario}")


def _stages_for_classification(classification: str) -> list[str]:
    if classification == "timeout":
        return [
            "before_request_constructed",
            "request_constructed",
            "request_sent",
            "timeout_detected",
            "exception_raised",
        ]
    stages = [
        "before_request_constructed",
        "request_constructed",
        "request_sent",
        "status_received",
        "parse_started",
    ]
    if classification in {"success_json", "http_error_json"}:
        stages.append("parse_completed")
    else:
        stages.append("parse_failed")
    return stages


def _reconciliation_behavior(
    classification: str,
) -> LambdaOwnedResourceReconciliationBehavior:
    if classification == "timeout":
        return "no_candidate_manual_review"
    if classification in {"http_error_json", "http_error_non_json"}:
        return "status_error_no_retry"
    return "schema_failure_manual_review"


def load_lambda_response_loss_regression_report(
    path: str | Path,
) -> LambdaResponseLossRegressionReport:
    return LambdaResponseLossRegressionReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_response_loss_regression_report(
    path: str | Path,
    report: LambdaResponseLossRegressionReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
