"""Launch transport diagnostics for response-loss analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_redaction import redact_lambda_payload

LambdaLaunchTransportFailureKind = Literal[
    "timeout",
    "malformed_response",
    "http_error",
    "transport_error",
    "unknown",
]


class LambdaLaunchTransportDiagnosticsReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    timeout_seconds: float | None = None
    request_sent_timestamp_utc: str | None = None
    exception_type: str | None = None
    http_status: int | None = None
    response_headers_redacted: dict[str, str] = Field(default_factory=dict)
    response_content_type: str | None = None
    response_body_size: int | None = None
    failure_kind: LambdaLaunchTransportFailureKind = "unknown"
    parse_failure_distinguished: bool = False
    socket_timeout_distinguished: bool = False
    secrets_redacted: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaLaunchTransportDiagnosticsReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("transport diagnostics cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_transport_diagnostics(
    *,
    timeout_seconds: float | None = None,
    request_sent_timestamp_utc: str | None = None,
    exception_type: str | None = None,
    http_status: int | None = None,
    response_headers: dict[str, str] | None = None,
    response_content_type: str | None = None,
    response_body_size: int | None = None,
    parse_failed: bool = False,
) -> LambdaLaunchTransportDiagnosticsReport:
    lowered_exception = (exception_type or "").lower()
    if "timeout" in lowered_exception:
        failure_kind: LambdaLaunchTransportFailureKind = "timeout"
    elif parse_failed:
        failure_kind = "malformed_response"
    elif http_status is not None and http_status >= 400:
        failure_kind = "http_error"
    elif exception_type:
        failure_kind = "transport_error"
    else:
        failure_kind = "unknown"
    redacted_headers = redact_lambda_payload(response_headers or {})
    return LambdaLaunchTransportDiagnosticsReport(
        timeout_seconds=timeout_seconds,
        request_sent_timestamp_utc=request_sent_timestamp_utc,
        exception_type=exception_type,
        http_status=http_status,
        response_headers_redacted={
            str(key): str(value) for key, value in redacted_headers.items()
        },
        response_content_type=response_content_type,
        response_body_size=response_body_size,
        failure_kind=failure_kind,
        parse_failure_distinguished=parse_failed,
        socket_timeout_distinguished=failure_kind == "timeout",
        warnings=[] if failure_kind != "unknown" else ["transport failure kind unknown"],
    )


def load_lambda_launch_transport_diagnostics(
    path: str | Path,
) -> LambdaLaunchTransportDiagnosticsReport:
    return LambdaLaunchTransportDiagnosticsReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_launch_transport_diagnostics(
    path: str | Path,
    report: LambdaLaunchTransportDiagnosticsReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
