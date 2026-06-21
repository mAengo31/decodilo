"""Secret-handling review for M025 Lambda pre-launch evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

_SECRET_RE = re.compile(
    r"(Authorization|Bearer\s+\S+|api[_-]?key\s*[:=]\s*['\"][^'\"]+|AKIA[0-9A-Z]{12,})",
    re.IGNORECASE,
)


class LambdaSecretHandlingReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_schema_version: int = 1
    review_id: str = "lambda-secret-handling-review-m025"
    scanned_refs: list[str] = Field(default_factory=list)
    secret_handling_passed: bool
    env_file_policy: str = "explicit .env only; no OS environment reads"
    cli_raw_api_key_rejected: bool = True
    secret_like_findings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSecretHandlingReport = LambdaSecretHandlingReview


def review_lambda_secret_handling(
    refs: list[str | Path],
) -> LambdaSecretHandlingReview:
    findings: list[str] = []
    scanned: list[str] = []
    for ref in refs:
        path = Path(ref)
        scanned.append(str(path))
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _SECRET_RE.search(text):
            findings.append(str(path))
    blockers = [f"secret-like value found in {item}" for item in findings]
    return LambdaSecretHandlingReview(
        scanned_refs=scanned,
        secret_handling_passed=not blockers,
        secret_like_findings=findings,
        blockers=blockers,
        warnings=["Secret review does not read OS environment variables."],
    )


def load_lambda_secret_handling_review(path: str | Path) -> LambdaSecretHandlingReview:
    return LambdaSecretHandlingReview.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_secret_handling_review(
    path: str | Path,
    review: LambdaSecretHandlingReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(review.to_json(), encoding="utf-8")
