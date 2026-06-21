"""M036 ambiguous-response semantics evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.support_confirmation_response import (
    LambdaSupportConfirmationResponse,
    load_lambda_support_confirmation_response,
)


class LambdaAmbiguousResponseSemantics(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_timeout_may_create_instance: bool | None
    terminate_timeout_may_terminate_instance: bool | None
    recommended_reconciliation_steps: list[str]
    manual_review_trigger_required: bool
    confidence: str
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaAmbiguousResponseSemantics:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("ambiguous-response evidence cannot enable launch")
        if self.launch_timeout_may_create_instance is None:
            raise ValueError("ambiguous launch behavior is required")
        if self.launch_timeout_may_create_instance and not self.manual_review_trigger_required:
            raise ValueError("ambiguous launch may create instance; manual review is required")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ambiguous_response_semantics(
    response: LambdaSupportConfirmationResponse,
) -> LambdaAmbiguousResponseSemantics:
    answers = response.answer_map()
    launch = answers.get("launch_timeout_may_create")
    terminate = answers.get("terminate_timeout_may_terminate")
    reconcile = answers.get("ambiguous_launch_reconciliation")
    blockers: list[str] = []
    launch_may = _maybe_bool(launch)
    terminate_may = _maybe_bool(terminate)
    if launch_may is None:
        blockers.append("ambiguous_launch_behavior_missing")
    steps = []
    if reconcile is not None and reconcile.answer_text:
        steps.append(reconcile.answer_text)
    else:
        steps.append("run read-only discovery and require manual console review on uncertainty")
        blockers.append("ambiguous_launch_reconciliation_missing")
    manual_required = True
    return LambdaAmbiguousResponseSemantics(
        launch_timeout_may_create_instance=launch_may,
        terminate_timeout_may_terminate_instance=terminate_may,
        recommended_reconciliation_steps=steps,
        manual_review_trigger_required=manual_required,
        confidence=response.confidence,
        warnings=[
            "ambiguous launch responses must not trigger automatic retry",
        ],
        blockers=blockers,
    )


def build_lambda_ambiguous_response_semantics_from_path(
    response: str | Path,
) -> LambdaAmbiguousResponseSemantics:
    return build_lambda_ambiguous_response_semantics(
        load_lambda_support_confirmation_response(response)
    )


def _maybe_bool(answer: object | None) -> bool | None:
    if answer is None:
        return None
    structured = getattr(answer, "structured_value", {}) or {}
    if "value" in structured and isinstance(structured["value"], bool):
        return structured["value"]
    text = str(getattr(answer, "answer_text", "")).strip().lower()
    if not text:
        return None
    if text in {"true", "yes", "may", "possible", "can"}:
        return True
    if text in {"false", "no", "cannot", "not possible"}:
        return False
    return "may" in text or "can" in text or "possible" in text


def load_lambda_ambiguous_response_semantics(
    path: str | Path,
) -> LambdaAmbiguousResponseSemantics:
    return LambdaAmbiguousResponseSemantics.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ambiguous_response_semantics(
    path: str | Path,
    report: LambdaAmbiguousResponseSemantics,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")

