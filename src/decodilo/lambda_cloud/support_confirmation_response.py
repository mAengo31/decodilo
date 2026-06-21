"""M036 support/operator response ingestion."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSupportEvidenceSource = Literal[
    "lambda_support_ticket",
    "lambda_docs_excerpt",
    "operator_confirmed_docs",
    "operator_manual_confirmation",
    "unknown",
]
LambdaSupportConfidence = Literal["low", "medium", "high"]
_SECRET_RE = re.compile(
    r"(Authorization\s*:|Bearer\s+[A-Za-z0-9._~+/=-]+|LAMBDA_API_KEY|"
    r"api[_-]?key\s*[:=]\s*[A-Za-z0-9._~+/=-]+)",
    re.IGNORECASE,
)


class LambdaSupportAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    answer_text: str
    structured_value: dict[str, Any] = Field(default_factory=dict)
    answered: bool = True


class LambdaSupportConfirmationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    response_id: str = "lambda-m036-support-confirmation-response"
    source_type: LambdaSupportEvidenceSource
    source_reference: str | None = None
    captured_at_utc: str | None = None
    answered_questions: list[LambdaSupportAnswer] = Field(default_factory=list)
    unanswered_questions: list[str] = Field(default_factory=list)
    confidence: LambdaSupportConfidence = "low"
    raw_text_redacted: str | None = None
    notes: str | None = None
    secret_scan_passed: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_safe(self) -> LambdaSupportConfirmationResponse:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("support confirmation response cannot enable launch")
        text = self.model_dump_json()
        if _SECRET_RE.search(text):
            raise ValueError("support confirmation response contains secret-like text")
        if not self.secret_scan_passed:
            raise ValueError("support confirmation response failed secret scan")
        return self

    def answer_map(self) -> dict[str, LambdaSupportAnswer]:
        return {answer.question_id: answer for answer in self.answered_questions}

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def ingest_lambda_support_confirmation_response(
    payload: dict[str, Any],
) -> LambdaSupportConfirmationResponse:
    normalized = dict(payload)
    raw_text = normalized.get("raw_text_redacted")
    if isinstance(raw_text, str) and _SECRET_RE.search(raw_text):
        normalized["raw_text_redacted"] = _SECRET_RE.sub("[REDACTED]", raw_text)
    answers = normalized.pop("answers", None)
    if answers is not None and "answered_questions" not in normalized:
        normalized["answered_questions"] = _answers_from_mapping(answers)
    return LambdaSupportConfirmationResponse.model_validate(normalized)


def ingest_lambda_support_confirmation_response_from_path(
    path: str | Path,
) -> LambdaSupportConfirmationResponse:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return ingest_lambda_support_confirmation_response(payload)


def _answers_from_mapping(answers: Any) -> list[dict[str, Any]]:
    if isinstance(answers, list):
        return answers
    if not isinstance(answers, dict):
        raise ValueError("answers must be a mapping or list")
    result: list[dict[str, Any]] = []
    for question_id, answer in answers.items():
        if isinstance(answer, dict):
            result.append(
                {
                    "question_id": question_id,
                    "answer_text": str(answer.get("answer_text", "")),
                    "structured_value": answer.get("structured_value", {}),
                    "answered": bool(answer.get("answered", True)),
                }
            )
        else:
            result.append(
                {
                    "question_id": question_id,
                    "answer_text": str(answer),
                    "structured_value": {},
                    "answered": True,
                }
            )
    return result


def load_lambda_support_confirmation_response(
    path: str | Path,
) -> LambdaSupportConfirmationResponse:
    return LambdaSupportConfirmationResponse.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_support_confirmation_response(
    path: str | Path,
    response: LambdaSupportConfirmationResponse,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(response.to_json(), encoding="utf-8")

