"""Audit log for Lambda live read-only discovery."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_SECRET_LIKE = re.compile(r"(lambda[_-]?[a-z0-9]{16,}|Bearer\s+\S+|AKIA[0-9A-Z]{12,})")
_MUTATION_WORDS = ("launch", "terminate", "restart", "create", "delete")

LambdaReadOnlyAuditStatus = Literal["passed", "passed_with_read_failures", "failed"]


class LambdaReadOnlyAuditEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation: str
    method: str
    endpoint: str
    allowed: bool
    status_code: int | None = None
    live_api_used: bool
    mutation: bool = False
    request_body_present: bool = False
    secret_redacted: bool = True
    error: str | None = None


class LambdaReadOnlyAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    passed: bool
    status: LambdaReadOnlyAuditStatus = "passed"
    entries: list[LambdaReadOnlyAuditEntry] = Field(default_factory=list)
    read_operations: int = 0
    mutating_operations: int = 0
    billable_action_performed: bool = False
    secret_redacted: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def audit_lambda_read_only(entries: list[LambdaReadOnlyAuditEntry]) -> LambdaReadOnlyAuditReport:
    errors: list[str] = []
    warnings: list[str] = []
    for entry in entries:
        serialized = json.dumps(entry.model_dump(mode="json"), sort_keys=True)
        if entry.method.upper() != "GET":
            errors.append(f"non-GET request observed: {entry.operation}")
        if entry.mutation or any(word in entry.operation for word in _MUTATION_WORDS):
            errors.append(f"mutating operation observed: {entry.operation}")
        if entry.request_body_present:
            errors.append(f"request body observed for read-only operation: {entry.operation}")
        if not entry.allowed:
            errors.append(f"denied endpoint was attempted: {entry.operation}")
        if not entry.secret_redacted or _SECRET_LIKE.search(serialized):
            errors.append("secret-like value detected in Lambda audit entry")
        if entry.error or (entry.status_code is not None and entry.status_code >= 400):
            warnings.append(f"read-only endpoint failed: {entry.operation}")
    read_count = sum(1 for entry in entries if entry.method.upper() == "GET")
    mutation_count = sum(1 for entry in entries if entry.mutation)
    if not entries:
        warnings.append("no Lambda read-only audit entries were present")
    status: LambdaReadOnlyAuditStatus = "failed"
    if not errors:
        status = "passed_with_read_failures" if warnings else "passed"
    return LambdaReadOnlyAuditReport(
        passed=not errors,
        status=status,
        entries=entries,
        read_operations=read_count,
        mutating_operations=mutation_count,
        warnings=warnings,
        errors=errors,
    )


def load_lambda_read_only_audit_report(path: str | Path) -> LambdaReadOnlyAuditReport:
    return LambdaReadOnlyAuditReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_read_only_audit_report(
    path: str | Path,
    report: LambdaReadOnlyAuditReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
