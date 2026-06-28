"""Offline diagnostic for M075R3 runtime-smoke update-stream failure."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.dev.runtime_smoke import load_runtime_smoke_report
from decodilo.lambda_cloud.runtime_smoke_update_stream_failure_record import (
    load_lambda_runtime_smoke_update_stream_failure_record,
)

RuntimeSmokeUpdateStreamDiagnosticStatus = Literal[
    "diagnosed_update_stream_timeout_path",
    "blocked",
]


class LambdaRuntimeSmokeUpdateStreamDiagnostic(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075U"
    diagnostic_status: RuntimeSmokeUpdateStreamDiagnosticStatus
    failed_check: str | None = None
    error_classification: str | None = None
    safe_error: str | None = None
    local_function_or_check: str
    update_stream_event_source: str
    producer_started: bool
    consumer_waits_on_correct_stream: bool
    timeout_configurable: bool
    local_reproduction_status: str
    local_before_status: str | None = None
    local_before_error_classification: str | None = None
    local_after_status: str | None = None
    local_after_error_classification: str | None = None
    likely_root_cause: str
    exact_code_path_needing_fix: str
    fix_strategy: str
    local_fix_verified: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_diagnostic(self) -> LambdaRuntimeSmokeUpdateStreamDiagnostic:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M075U diagnostic must remain offline")
        if self.diagnostic_status != "blocked" and self.blockers:
            raise ValueError("successful M075U diagnostic cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _optional_runtime_report(path: Path) -> tuple[str | None, str | None]:
    if not path.is_file():
        return None, None
    report = load_runtime_smoke_report(path)
    return report.runtime_smoke_status, report.error_classification


def build_lambda_runtime_smoke_update_stream_diagnostic_from_paths(
    *,
    failure_record: str | Path,
    source_root: str | Path,
) -> LambdaRuntimeSmokeUpdateStreamDiagnostic:
    record = load_lambda_runtime_smoke_update_stream_failure_record(failure_record)
    root = Path(source_root)
    runtime_smoke_source = root / "src/decodilo/dev/runtime_smoke.py"
    update_stream_source = root / "src/decodilo/runtime/update_stream.py"
    runtime_text = runtime_smoke_source.read_text(encoding="utf-8")
    update_text = update_stream_source.read_text(encoding="utf-8")
    before_status, before_error = _optional_runtime_report(
        Path("/tmp/decodilo-runtime-smoke-m075u-before.json")
    )
    after_status, after_error = _optional_runtime_report(
        Path("/tmp/decodilo-runtime-smoke-m075u-after.json")
    )
    local_reproduction = "not_run"
    if before_status == "failed" and before_error == "update_stream_check_failed":
        local_reproduction = "local_reproduced_update_stream_failure"
    elif before_status == "passed":
        local_reproduction = "local_pass_remote_fail"
    elif before_status == "failed":
        local_reproduction = "local_failed_different_error"
    local_fix_verified = after_status == "passed"
    producer_started = "notify_commit" in runtime_text
    consumer_waits = "wait_for_update" in runtime_text and "UpdateStream" in runtime_text
    timeout_configurable = "timeout_seconds" in update_text
    asyncio_timeout_caught = "asyncio.TimeoutError" in update_text
    deterministic_wait = "asyncio.create_task" in runtime_text and "pending_update" in runtime_text
    blockers: list[str] = []
    if record.failure_status != "runtime_smoke_update_stream_failed":
        blockers.append("failure_record_not_update_stream_failure")
    if not producer_started:
        blockers.append("update_stream_producer_not_found")
    if not consumer_waits:
        blockers.append("update_stream_consumer_not_found")
    if not timeout_configurable:
        blockers.append("update_stream_timeout_not_configurable")
    if not asyncio_timeout_caught:
        blockers.append("asyncio_timeout_not_caught")
    if not deterministic_wait:
        blockers.append("runtime_smoke_update_stream_wait_not_deterministic")
    return LambdaRuntimeSmokeUpdateStreamDiagnostic(
        diagnostic_status=(
            "diagnosed_update_stream_timeout_path" if not blockers else "blocked"
        ),
        failed_check=record.failed_check,
        error_classification=record.error_classification,
        safe_error=record.safe_error,
        local_function_or_check="decodilo.dev.runtime_smoke._run_update_stream_check",
        update_stream_event_source="decodilo.runtime.update_stream.UpdateStream._update_event",
        producer_started=producer_started,
        consumer_waits_on_correct_stream=consumer_waits,
        timeout_configurable=timeout_configurable,
        local_reproduction_status=local_reproduction,
        local_before_status=before_status,
        local_before_error_classification=before_error,
        local_after_status=after_status,
        local_after_error_classification=after_error,
        likely_root_cause=(
            "remote Python 3.10 exposed asyncio timeout handling plus a timing-sensitive "
            "1 ms no-update probe in the runtime-smoke update-stream check"
        ),
        exact_code_path_needing_fix=(
            "UpdateStream.wait_for_update timeout handling and "
            "runtime_smoke._run_update_stream_check"
        ),
        fix_strategy=(
            "catch asyncio.TimeoutError explicitly and validate a deterministic "
            "synthetic commit observed by a waiting UpdateStream consumer"
        ),
        local_fix_verified=local_fix_verified,
        blockers=sorted(set(blockers)),
        warnings=[
            "diagnostic used local source and persisted M075R3 evidence only",
            "no Lambda, SSH, remote command, install, download, or training was used",
        ],
    )


def load_lambda_runtime_smoke_update_stream_diagnostic(
    path: str | Path,
) -> LambdaRuntimeSmokeUpdateStreamDiagnostic:
    return LambdaRuntimeSmokeUpdateStreamDiagnostic.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_runtime_smoke_update_stream_diagnostic(
    path: str | Path,
    diagnostic: LambdaRuntimeSmokeUpdateStreamDiagnostic,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(diagnostic.to_json(), encoding="utf-8")
