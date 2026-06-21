"""Validate M036 support/operator confirmation responses."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.support_confirmation_response import (
    LambdaSupportConfirmationResponse,
    load_lambda_support_confirmation_response,
)


class LambdaSupportConfirmationValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    validation_passed: bool
    endpoint_confidence_candidate: str
    answered_question_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaSupportConfirmationValidationReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("support confirmation validation cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def validate_lambda_support_confirmation_response(
    response: LambdaSupportConfirmationResponse,
) -> LambdaSupportConfirmationValidationReport:
    answers = response.answer_map()
    answered = sorted(answers)
    blockers: list[str] = []
    warnings: list[str] = []
    required = [
        "launch_method",
        "launch_path_template",
        "terminate_method",
        "terminate_path_template",
        "launch_success_status",
        "launch_response_shape",
        "ambiguous_launch_reconciliation",
        "launch_timeout_may_create",
        "termination_verification",
        "termination_terminal_states",
        "launch_rate_limits",
        "terminate_rate_limits",
        "safe_lifecycle_shape",
    ]
    for question_id in required:
        if not _answered(answers, question_id):
            blockers.append(f"missing_{question_id}")
    has_id = _answered(answers, "launch_instance_id_field")
    has_async = _answered(answers, "launch_async_without_id")
    if not has_id and not has_async:
        blockers.append("missing_instance_id_field_or_async_explanation")
    if response.confidence == "low":
        warnings.append("support response confidence is low")
    candidate = "high" if not blockers and response.confidence == "high" else "medium"
    if blockers:
        candidate = "low" if response.confidence == "low" else "medium"
    return LambdaSupportConfirmationValidationReport(
        validation_passed=not blockers,
        endpoint_confidence_candidate=candidate,
        answered_question_ids=answered,
        blockers=blockers,
        warnings=warnings,
    )


def validate_lambda_support_confirmation_response_from_path(
    response: str | Path,
) -> LambdaSupportConfirmationValidationReport:
    return validate_lambda_support_confirmation_response(
        load_lambda_support_confirmation_response(response)
    )


def _answered(
    answers: dict[str, object],
    question_id: str,
) -> bool:
    answer = answers.get(question_id)
    return bool(
        answer is not None
        and getattr(answer, "answered", False)
        and str(getattr(answer, "answer_text", "")).strip()
    )


def load_lambda_support_confirmation_validation_report(
    path: str | Path,
) -> LambdaSupportConfirmationValidationReport:
    return LambdaSupportConfirmationValidationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_support_confirmation_validation_report(
    path: str | Path,
    report: LambdaSupportConfirmationValidationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")

