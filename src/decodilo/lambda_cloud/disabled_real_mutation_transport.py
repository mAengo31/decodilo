"""Disabled real Lambda mutation transport skeleton."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.real_mutation_transport_interface import (
    LambdaRealMutationOperationResult,
)


class LambdaRealMutationDisabledReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    attempted_operation: str
    blocked_before_request_construction: bool = True
    request_constructed: bool = False
    url_constructed: bool = False
    http_method_constructed: bool = False
    request_body_constructed: bool = False
    credential_accessed: bool = False
    network_accessed: bool = False
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRealMutationDisabledError(RuntimeError):
    """Raised before any real Lambda mutation request construction."""

    def __init__(self, report: LambdaRealMutationDisabledReport) -> None:
        self.report = report
        super().__init__(
            f"Lambda real mutation operation is disabled: {report.attempted_operation}"
        )


class DisabledLambdaRealMutationTransport:
    """Skeleton transport that cannot construct or send real mutation requests."""

    def __init__(self) -> None:
        self.last_report: LambdaRealMutationDisabledReport | None = None

    def launch_one_instance(self, *args: object, **kwargs: object) -> None:
        self._raise_disabled("launch_one_instance")

    def terminate_owned_instance(self, *args: object, **kwargs: object) -> None:
        self._raise_disabled("terminate_owned_instance")

    def restart_instance(self, *args: object, **kwargs: object) -> None:
        self._raise_disabled("restart_instance")

    def create_ssh_key(self, *args: object, **kwargs: object) -> None:
        self._raise_disabled("create_ssh_key")

    def delete_ssh_key(self, *args: object, **kwargs: object) -> None:
        self._raise_disabled("delete_ssh_key")

    def create_filesystem(self, *args: object, **kwargs: object) -> None:
        self._raise_disabled("create_filesystem")

    def delete_filesystem(self, *args: object, **kwargs: object) -> None:
        self._raise_disabled("delete_filesystem")

    def disabled_result(self, operation_name: str) -> LambdaRealMutationOperationResult:
        return LambdaRealMutationOperationResult(
            operation_name=operation_name,
            errors=["real Lambda mutation transport is disabled in M024"],
        )

    def _raise_disabled(self, operation_name: str) -> None:
        report = LambdaRealMutationDisabledReport(
            attempted_operation=operation_name,
            errors=["blocked before request construction"],
        )
        self.last_report = report
        raise LambdaRealMutationDisabledError(report)


def write_lambda_real_mutation_disabled_report(
    path: str | Path,
    report: LambdaRealMutationDisabledReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
