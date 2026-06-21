"""M036 idempotency semantics evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.support_confirmation_response import (
    LambdaSupportConfirmationResponse,
    load_lambda_support_confirmation_response,
)


class LambdaIdempotencySemanticsEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    idempotency_supported: bool | None
    idempotency_field_name: str | None = None
    client_token_supported: bool | None = None
    duplicate_launch_behavior: str
    duplicate_terminate_behavior: str
    confidence: str
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaIdempotencySemanticsEvidence:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("idempotency evidence cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_idempotency_semantics_evidence(
    response: LambdaSupportConfirmationResponse,
) -> LambdaIdempotencySemanticsEvidence:
    answer = response.answer_map().get("launch_idempotency")
    structured = {} if answer is None else answer.structured_value
    supported = structured.get("idempotency_supported")
    field_name = structured.get("field_name") or structured.get("idempotency_field_name")
    client_token = structured.get("client_token_supported")
    warnings: list[str] = []
    if supported is None:
        warnings.append(
            "idempotency support unknown; future launches must rely on no retry plus reconciliation"
        )
    return LambdaIdempotencySemanticsEvidence(
        idempotency_supported=supported,
        idempotency_field_name=None if field_name is None else str(field_name),
        client_token_supported=client_token,
        duplicate_launch_behavior=str(
            structured.get(
                "duplicate_launch_behavior",
                "unknown; do not automatically retry launch",
            )
        ),
        duplicate_terminate_behavior=str(
            structured.get(
                "duplicate_terminate_behavior",
                "verify owned resource through read-only discovery",
            )
        ),
        confidence=response.confidence,
        warnings=warnings,
    )


def build_lambda_idempotency_semantics_evidence_from_path(
    response: str | Path,
) -> LambdaIdempotencySemanticsEvidence:
    return build_lambda_idempotency_semantics_evidence(
        load_lambda_support_confirmation_response(response)
    )


def load_lambda_idempotency_semantics_evidence(
    path: str | Path,
) -> LambdaIdempotencySemanticsEvidence:
    return LambdaIdempotencySemanticsEvidence.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_idempotency_semantics_evidence(
    path: str | Path,
    report: LambdaIdempotencySemanticsEvidence,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")

