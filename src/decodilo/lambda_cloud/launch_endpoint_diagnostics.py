"""Review-only endpoint diagnostics for future launch attempts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

_ALLOWED_LAUNCH_METHODS = {"POST"}
_ALLOWED_TERMINATE_METHODS = {"DELETE"}


class LambdaLaunchEndpointDiagnosticsReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_endpoint_path: str | None = None
    launch_http_method: str | None = None
    terminate_endpoint_path: str | None = None
    terminate_http_method: str | None = None
    operation_spec_verified: bool = False
    docs_or_operator_verified: bool = False
    endpoint_diagnostics_passed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaLaunchEndpointDiagnosticsReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("endpoint diagnostics cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_endpoint_diagnostics(
    *,
    launch_endpoint_path: str | None,
    launch_http_method: str | None,
    terminate_endpoint_path: str | None,
    terminate_http_method: str | None,
    operation_spec_verified: bool = False,
    docs_or_operator_verified: bool = False,
) -> LambdaLaunchEndpointDiagnosticsReport:
    blockers: list[str] = []
    warnings: list[str] = []
    launch_method = (launch_http_method or "").upper()
    terminate_method = (terminate_http_method or "").upper()
    if not launch_endpoint_path:
        blockers.append("launch endpoint path missing")
    if not terminate_endpoint_path:
        blockers.append("terminate endpoint path missing")
    if launch_method not in _ALLOWED_LAUNCH_METHODS:
        blockers.append("launch method not allowed by M031D diagnostics")
    if terminate_method not in _ALLOWED_TERMINATE_METHODS:
        blockers.append("terminate method not allowed by M031D diagnostics")
    if not operation_spec_verified:
        blockers.append("endpoint mapping not verified against operation spec")
    if not docs_or_operator_verified:
        warnings.append("endpoint mapping not verified against live docs/operator")
    return LambdaLaunchEndpointDiagnosticsReport(
        launch_endpoint_path=launch_endpoint_path,
        launch_http_method=launch_method or None,
        terminate_endpoint_path=terminate_endpoint_path,
        terminate_http_method=terminate_method or None,
        operation_spec_verified=operation_spec_verified,
        docs_or_operator_verified=docs_or_operator_verified,
        endpoint_diagnostics_passed=not blockers,
        blockers=blockers,
        warnings=warnings,
    )


def load_lambda_launch_endpoint_diagnostics(
    path: str | Path,
) -> LambdaLaunchEndpointDiagnosticsReport:
    return LambdaLaunchEndpointDiagnosticsReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_launch_endpoint_diagnostics(
    path: str | Path,
    report: LambdaLaunchEndpointDiagnosticsReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
