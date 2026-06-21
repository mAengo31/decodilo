"""Verify review-only endpoint specs without calling mutation endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_endpoint_spec import (
    LambdaEndpointOperationSpec,
    load_lambda_endpoint_spec,
)


class LambdaEndpointVerificationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    endpoint_specs: list[LambdaEndpointOperationSpec] = Field(default_factory=list)
    endpoint_verification_passed: bool
    verified_operations: list[str] = Field(default_factory=list)
    confidence: str = "unknown"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    live_mutation_call_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaEndpointVerificationReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("endpoint verification cannot enable launch")
        if self.live_mutation_call_performed:
            raise ValueError("endpoint verification cannot perform live mutation calls")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def verify_lambda_endpoint_specs(
    specs: list[LambdaEndpointOperationSpec],
) -> LambdaEndpointVerificationReport:
    blockers: list[str] = []
    warnings: list[str] = []
    verified: list[str] = []
    confidence_rank = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    min_confidence = "unknown"
    for spec in specs:
        method = spec.method.upper()
        if spec.operation == "launch_one_instance" and method != "POST":
            blockers.append("launch endpoint method must be POST")
        if spec.operation == "terminate_owned_instance" and method not in {"DELETE", "POST"}:
            blockers.append("terminate endpoint method must be DELETE or documented POST")
        if spec.confidence in {"unknown", "low"}:
            blockers.append(f"{spec.operation} endpoint confidence too low")
        if not spec.verified_for_real_mutation:
            blockers.append(f"{spec.operation} endpoint not verified for future mutation")
        if not spec.source_url and spec.source == "unknown":
            warnings.append(f"{spec.operation} endpoint source is unknown")
        if spec.source == "unofficial_cli_behavior":
            warnings.append(
                f"{spec.operation} endpoint source is unofficial behavioral evidence"
            )
        verified.append(spec.operation)
    if specs:
        min_confidence = min(
            [spec.confidence for spec in specs],
            key=lambda item: confidence_rank[item],
        )
    else:
        blockers.append("no endpoint specs provided")
    return LambdaEndpointVerificationReport(
        endpoint_specs=specs,
        endpoint_verification_passed=not blockers,
        verified_operations=verified,
        confidence=min_confidence,
        blockers=blockers,
        warnings=warnings,
    )


def verify_lambda_endpoint_specs_from_paths(
    paths: list[str | Path],
) -> LambdaEndpointVerificationReport:
    return verify_lambda_endpoint_specs([load_lambda_endpoint_spec(path) for path in paths])


def load_lambda_endpoint_verification_report(
    path: str | Path,
) -> LambdaEndpointVerificationReport:
    return LambdaEndpointVerificationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_endpoint_verification_report(
    path: str | Path,
    report: LambdaEndpointVerificationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
