"""Build redacted response-loss diagnostic fixtures for offline regression tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.http_response_capture import (
    LambdaHTTPResponseCapture,
    capture_lambda_http_response,
)

LambdaResponseLossFixtureScenario = Literal[
    "launch_timeout_before_status",
    "launch_status_200_empty_body",
    "launch_status_200_non_json_body",
    "launch_status_202_json_unexpected_schema",
    "launch_status_4xx_json_error",
    "launch_status_5xx_non_json",
    "terminate_timeout_before_status",
    "terminate_status_200_empty_body",
    "terminate_status_202_json_unexpected_schema",
]


class LambdaResponseLossDiagnosticFixture(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    scenario: LambdaResponseLossFixtureScenario
    operation: str
    response_capture: LambdaHTTPResponseCapture
    no_real_lambda_call: bool = True
    no_secret_leakage: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_response_loss_diagnostic_fixture(
    scenario: LambdaResponseLossFixtureScenario,
) -> LambdaResponseLossDiagnosticFixture:
    operation = (
        "terminate_owned_instance"
        if scenario.startswith("terminate_")
        else "launch_one_instance"
    )
    endpoint = (
        "/instance-operations/terminate"
        if operation == "terminate_owned_instance"
        else "/instance-operations/launch"
    )
    capture = _capture_for_scenario(scenario, operation=operation, endpoint=endpoint)
    return LambdaResponseLossDiagnosticFixture(
        scenario=scenario,
        operation=operation,
        response_capture=capture,
        warnings=[] if capture.classification != "schema_validation_failure" else [
            "fixture intentionally uses valid JSON with unexpected schema"
        ],
    )


def _capture_for_scenario(
    scenario: LambdaResponseLossFixtureScenario,
    *,
    operation: str,
    endpoint: str,
) -> LambdaHTTPResponseCapture:
    common = {
        "method": "POST" if operation == "launch_one_instance" else "DELETE",
        "endpoint_path_template": endpoint,
        "endpoint_path": endpoint,
        "mutation_operation_name": operation,
        "headers": {"Content-Type": "application/json"},
    }
    if scenario.endswith("timeout_before_status"):
        return capture_lambda_http_response(
            **common,
            exception_type="TimeoutError",
            exception_message="fake timeout before status",
            status_code=None,
        )
    if scenario.endswith("200_empty_body"):
        return capture_lambda_http_response(**common, status_code=200, body=b"")
    if scenario.endswith("200_non_json_body"):
        return capture_lambda_http_response(
            **{**common, "headers": {"Content-Type": "text/plain"}},
            status_code=200,
            body=b"ok",
        )
    if scenario.endswith("202_json_unexpected_schema"):
        return capture_lambda_http_response(
            **common,
            status_code=202,
            body=b'{"data":{"unexpected":true}}',
            schema_validation_failed=True,
        )
    if scenario.endswith("4xx_json_error"):
        return capture_lambda_http_response(
            **common,
            status_code=400,
            body=b'{"error":{"message":"bad request"}}',
        )
    if scenario.endswith("5xx_non_json"):
        return capture_lambda_http_response(
            **{**common, "headers": {"Content-Type": "text/plain"}},
            status_code=500,
            body=b"server error",
        )
    raise ValueError(f"unsupported response-loss scenario: {scenario}")


def write_lambda_response_loss_diagnostic_fixture(
    path: str | Path,
    fixture: LambdaResponseLossDiagnosticFixture,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(fixture.to_json(), encoding="utf-8")
