"""Endpoint behavior evidence derived from validated support confirmation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.support_confirmation_response import (
    LambdaSupportConfirmationResponse,
    load_lambda_support_confirmation_response,
)
from decodilo.lambda_cloud.support_confirmation_validator import (
    LambdaSupportConfirmationValidationReport,
    load_lambda_support_confirmation_validation_report,
)


class LambdaEndpointBehaviorEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_method: str
    launch_path_template: str
    launch_expected_status_codes: list[int]
    launch_expected_content_types: list[str]
    launch_response_instance_id_field: str | None = None
    launch_async_without_id_possible: bool = False
    terminate_method: str
    terminate_path_template: str
    terminate_expected_status_codes: list[int]
    terminate_terminal_states: list[str]
    list_instances_endpoint: str | None = None
    pagination_behavior: str | None = None
    region_scope_behavior: str | None = None
    evidence_confidence: str
    evidence_source_ref: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaEndpointBehaviorEvidence:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("endpoint behavior evidence cannot enable launch")
        if (
            not self.launch_response_instance_id_field
            and not self.launch_async_without_id_possible
            and not self.blockers
        ):
            raise ValueError("instance ID field or async/no-ID explanation required")
        if not self.terminate_terminal_states and not self.blockers:
            raise ValueError("terminate terminal states required")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_endpoint_behavior_evidence(
    *,
    response: LambdaSupportConfirmationResponse,
    validation: LambdaSupportConfirmationValidationReport,
) -> LambdaEndpointBehaviorEvidence:
    answers = response.answer_map()
    blockers = list(validation.blockers)
    return LambdaEndpointBehaviorEvidence(
        launch_method=_text(answers, "launch_method", "POST").upper(),
        launch_path_template=_text(
            answers,
            "launch_path_template",
            "/instance-operations/launch",
        ),
        launch_expected_status_codes=_int_list(answers, "launch_success_status", [200, 202]),
        launch_expected_content_types=_str_list(
            answers,
            "launch_content_type",
            ["application/json"],
        ),
        launch_response_instance_id_field=_optional_text(
            answers,
            "launch_instance_id_field",
        ),
        launch_async_without_id_possible=_bool(answers, "launch_async_without_id", False),
        terminate_method=_text(answers, "terminate_method", "POST").upper(),
        terminate_path_template=_text(
            answers,
            "terminate_path_template",
            "/instance-operations/terminate",
        ),
        terminate_expected_status_codes=_int_list(
            answers,
            "terminate_success_status",
            [200, 202, 204],
        ),
        terminate_terminal_states=_str_list(
            answers,
            "termination_terminal_states",
            ["terminated"],
        ),
        list_instances_endpoint=_optional_text(answers, "list_instances_endpoint"),
        pagination_behavior=_optional_text(answers, "list_pagination"),
        region_scope_behavior=_optional_text(answers, "list_region_scope"),
        evidence_confidence=validation.endpoint_confidence_candidate,
        evidence_source_ref=response.source_reference,
        blockers=blockers,
        warnings=validation.warnings,
    )


def build_lambda_endpoint_behavior_evidence_from_paths(
    *,
    response: str | Path,
    validation: str | Path,
) -> LambdaEndpointBehaviorEvidence:
    return build_lambda_endpoint_behavior_evidence(
        response=load_lambda_support_confirmation_response(response),
        validation=load_lambda_support_confirmation_validation_report(validation),
    )


def _answer_value(answers: dict[str, Any], question_id: str) -> Any:
    answer = answers.get(question_id)
    if answer is None:
        return None
    structured = getattr(answer, "structured_value", {}) or {}
    if "value" in structured:
        return structured["value"]
    if "values" in structured:
        return structured["values"]
    return getattr(answer, "answer_text", None)


def _text(answers: dict[str, Any], question_id: str, default: str) -> str:
    value = _answer_value(answers, question_id)
    return default if _missing_value(value) else str(value)


def _optional_text(answers: dict[str, Any], question_id: str) -> str | None:
    value = _answer_value(answers, question_id)
    return None if _missing_value(value) else str(value)


def _bool(answers: dict[str, Any], question_id: str, default: bool) -> bool:
    value = _answer_value(answers, question_id)
    if isinstance(value, bool):
        return value
    if _missing_value(value):
        return default
    return str(value).strip().lower() in {"true", "yes", "1", "supported"}


def _int_list(answers: dict[str, Any], question_id: str, default: list[int]) -> list[int]:
    value = _answer_value(answers, question_id)
    if _missing_value(value):
        return default
    if isinstance(value, list):
        return [int(item) for item in value]
    return [int(part.strip()) for part in str(value).replace("/", ",").split(",") if part.strip()]


def _str_list(answers: dict[str, Any], question_id: str, default: list[str]) -> list[str]:
    value = _answer_value(answers, question_id)
    if _missing_value(value):
        return default
    if isinstance(value, list):
        return [str(item) for item in value]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _missing_value(value: Any) -> bool:
    return value is None or value == ""


def load_lambda_endpoint_behavior_evidence(
    path: str | Path,
) -> LambdaEndpointBehaviorEvidence:
    return LambdaEndpointBehaviorEvidence.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_endpoint_behavior_evidence(
    path: str | Path,
    report: LambdaEndpointBehaviorEvidence,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
