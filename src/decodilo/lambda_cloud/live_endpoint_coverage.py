"""Endpoint coverage reports for Lambda read-only discovery."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.endpoint_calibration import LambdaEndpointResult


class LambdaEndpointCoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    endpoint_set: str
    endpoints_expected: list[str] = Field(default_factory=list)
    endpoints_attempted: list[str] = Field(default_factory=list)
    endpoints_succeeded: list[str] = Field(default_factory=list)
    endpoints_failed: list[str] = Field(default_factory=list)
    endpoints_not_attempted: list[str] = Field(default_factory=list)
    coverage_ratio: float
    live_api_used: bool
    mutation: bool = False
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_endpoint_coverage_report(
    *,
    endpoint_set: str,
    expected_operations: list[str],
    results: list[LambdaEndpointResult],
) -> LambdaEndpointCoverageReport:
    attempted = [result.operation for result in results if result.attempted]
    succeeded = [result.operation for result in results if result.success]
    failed = [result.operation for result in results if result.attempted and not result.success]
    expected = list(dict.fromkeys(expected_operations))
    not_attempted = [operation for operation in expected if operation not in attempted]
    denominator = max(len(expected), 1)
    return LambdaEndpointCoverageReport(
        endpoint_set=endpoint_set,
        endpoints_expected=expected,
        endpoints_attempted=attempted,
        endpoints_succeeded=succeeded,
        endpoints_failed=failed,
        endpoints_not_attempted=not_attempted,
        coverage_ratio=len([op for op in expected if op in attempted]) / denominator,
        live_api_used=any(result.live_api_used for result in results),
        mutation=any(result.mutation for result in results),
        billable_action_performed=any(result.billable_action_performed for result in results),
        warnings=[] if not failed else ["one or more read-only endpoints failed"],
    )


def load_lambda_endpoint_coverage_report(path: str | Path) -> LambdaEndpointCoverageReport:
    return LambdaEndpointCoverageReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
