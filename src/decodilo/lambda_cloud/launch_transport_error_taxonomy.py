"""Classification helpers for Lambda launch transport failures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaLaunchTransportErrorType = Literal[
    "http_4xx",
    "http_5xx",
    "timeout",
    "connection_error",
    "malformed_json",
    "non_json_response",
    "empty_response",
    "schema_validation_failure",
    "unknown",
]


class LambdaLaunchTransportErrorTaxonomyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    error_type: LambdaLaunchTransportErrorType
    status_code: int | None = None
    response_classification: str | None = None
    exception_type: str | None = None
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaLaunchTransportErrorTaxonomyReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("launch transport error taxonomy cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def classify_lambda_launch_transport_error(
    *,
    status_code: int | None = None,
    response_classification: str | None = None,
    exception_type: str | None = None,
) -> LambdaLaunchTransportErrorTaxonomyReport:
    lowered_exception = (exception_type or "").lower()
    classification = response_classification or ""
    if "timeout" in lowered_exception or classification == "timeout":
        error_type: LambdaLaunchTransportErrorType = "timeout"
    elif status_code is not None and 400 <= status_code < 500:
        error_type = "http_4xx"
    elif status_code is not None and status_code >= 500:
        error_type = "http_5xx"
    elif classification == "malformed_json":
        error_type = "malformed_json"
    elif classification in {"success_non_json", "http_error_non_json"}:
        error_type = "non_json_response"
    elif classification == "success_empty_body":
        error_type = "empty_response"
    elif classification == "schema_validation_failure":
        error_type = "schema_validation_failure"
    elif exception_type and status_code is None:
        error_type = "connection_error"
    else:
        error_type = "unknown"
    return LambdaLaunchTransportErrorTaxonomyReport(
        error_type=error_type,
        status_code=status_code,
        response_classification=response_classification,
        exception_type=exception_type,
    )


def write_lambda_launch_transport_error_taxonomy(
    path: str | Path,
    report: LambdaLaunchTransportErrorTaxonomyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
