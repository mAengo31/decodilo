"""M035 support/operator evidence request for Lambda launch behavior."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaSupportQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    question: str
    why_needed: str


class LambdaSupportEvidenceRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = "lambda-m035-support-evidence-request"
    provider: str = "lambda"
    questions: list[LambdaSupportQuestion]
    no_secrets_included: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaSupportEvidenceRequest:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("support evidence request cannot enable launch")
        if not self.no_secrets_included:
            raise ValueError("support evidence request must not include secrets")
        return self


class LambdaSupportEvidenceRequestReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    support_request: LambdaSupportEvidenceRequest
    support_request_generated: bool
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaSupportEvidenceRequestReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M035 support request cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_support_evidence_request() -> LambdaSupportEvidenceRequestReport:
    questions = [
        ("launch_endpoint", "What is the correct launch endpoint path and method?"),
        ("launch_response", "What response shape should launch return?"),
        (
            "ambiguous_response",
            "Under what conditions can launch return no body, non-JSON, or timeout "
            "while still creating an instance?",
        ),
        ("idempotency", "How should idempotency be handled?"),
        ("owned_id", "What fields identify the launched instance?"),
        (
            "availability_endpoint",
            "Is there an account-specific instance type or availability endpoint?",
        ),
        ("quota_usage", "Are quota/usage endpoints supported for this account?"),
        (
            "termination_states",
            "What terminal states indicate successful termination?",
        ),
        ("rate_limits", "What rate limits apply to launch and terminate?"),
    ]
    return LambdaSupportEvidenceRequestReport(
        support_request=LambdaSupportEvidenceRequest(
            questions=[
                LambdaSupportQuestion(
                    question_id=question_id,
                    question=question,
                    why_needed="Needed before considering another billable launch attempt.",
                )
                for question_id, question in questions
            ]
        ),
        support_request_generated=True,
        warnings=[
            "support request is non-executing evidence; it does not call Lambda APIs"
        ],
    )


def load_lambda_support_evidence_request_report(
    path: str | Path,
) -> LambdaSupportEvidenceRequestReport:
    return LambdaSupportEvidenceRequestReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_support_evidence_request_report(
    path: str | Path,
    report: LambdaSupportEvidenceRequestReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
