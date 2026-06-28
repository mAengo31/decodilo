"""Classify remote vertical-slice upload failures without live access."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaUploadFailureClassification = Literal[
    "ssh_banner_exchange_timeout_during_upload",
    "scp_connection_closed_during_upload",
    "upload_failed_unknown",
    "not_an_upload_failure",
]

_BANNER_TIMEOUT_PATTERNS = (
    "connection timed out during banner exchange",
    "banner exchange timeout",
    "kex_exchange_identification",
)
_SCP_CLOSED_PATTERNS = (
    "scp: connection closed",
    "connection closed by remote host",
)


class LambdaRemoteVSliceUploadFailureClassification(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M073S"
    classification_status: str
    failure_stage: str | None = None
    source_bundle_upload_attempted: bool
    source_bundle_upload_verified: bool
    dependency_bundle_upload_attempted: bool
    manifest_started: bool
    tiny_smoke_attempted: bool
    raw_error_redacted: bool
    redacted_error_summary: str | None = None
    failure_classification: LambdaUploadFailureClassification
    decodilo_tested: bool
    no_training: bool
    termination_verified: bool
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_classification(self) -> LambdaRemoteVSliceUploadFailureClassification:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M073S classification must not authorize launch or spend")
        if self.classification_status == "classified" and self.blockers:
            raise ValueError("classified upload failure cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_report(workdir: Path) -> dict[str, Any]:
    return _read_json(workdir / "report.json")


def _load_evidence(workdir: Path) -> dict[str, Any]:
    path = workdir / "remote-vslice-evidence.json"
    if not path.exists():
        path = workdir / "ssh-connectivity-evidence.json"
    return _read_json(path) if path.exists() else {}


def _load_post_summary(workdir: Path) -> dict[str, Any]:
    candidates = [
        workdir / "post-discovery-summary-final.json",
        workdir / "post-discovery-summary.json",
    ]
    if workdir.name == "decodilo-lambda-m073r":
        candidates.extend(
            sorted(
                Path("/tmp").glob("decodilo-lambda-post-m073r-summary-final-*.json"),
                reverse=True,
            )
        )
        candidates.append(Path("/tmp/decodilo-lambda-post-m073r-summary-final-4.json"))
    for path in candidates:
        if path.exists():
            return _read_json(path)
    return {}


def classify_upload_failure_text(text: str) -> LambdaUploadFailureClassification:
    normalized = text.lower()
    if any(pattern in normalized for pattern in _BANNER_TIMEOUT_PATTERNS):
        return "ssh_banner_exchange_timeout_during_upload"
    if any(pattern in normalized for pattern in _SCP_CLOSED_PATTERNS):
        return "scp_connection_closed_during_upload"
    return "upload_failed_unknown" if normalized.strip() else "not_an_upload_failure"


def build_lambda_upload_failure_classification_from_workdir(
    *,
    workdir: str | Path,
) -> LambdaRemoteVSliceUploadFailureClassification:
    run_dir = Path(workdir)
    report = _load_report(run_dir)
    evidence = _load_evidence(run_dir)
    post_summary = _load_post_summary(run_dir)

    stage_results = report.get("remote_command_stage_results") or []
    stage_names = [
        result.get("stage")
        for result in stage_results
        if isinstance(result, dict) and result.get("stage")
    ]
    redacted_stderr = str(evidence.get("stderr_redacted") or "")
    error_summary = "; ".join(str(item) for item in report.get("errors") or [])
    combined_error_text = "\n".join(part for part in [redacted_stderr, error_summary] if part)
    failure_classification = classify_upload_failure_text(combined_error_text)
    failed_stage = report.get("failed_stage")
    source_upload_attempted = bool(report.get("source_bundle_upload_attempted"))
    source_upload_verified = bool(report.get("source_bundle_hash_verified"))
    dependency_upload_attempted = bool(report.get("dependency_bundle_upload_attempted"))
    tiny_smoke_attempted = "tiny_smoke_command" in stage_names
    decodilo_tested = bool(stage_results)
    blockers: list[str] = []
    if failed_stage != "source_bundle_upload":
        blockers.append("failure_stage_not_source_bundle_upload")
    if not source_upload_attempted:
        blockers.append("source_bundle_upload_not_attempted")
    if source_upload_verified:
        blockers.append("source_bundle_unexpectedly_verified")
    if dependency_upload_attempted:
        blockers.append("dependency_upload_attempted_after_source_failure")
    if tiny_smoke_attempted:
        blockers.append("tiny_smoke_attempted_after_source_failure")
    if not report.get("termination_verified"):
        blockers.append("termination_not_verified")
    if failure_classification == "not_an_upload_failure":
        blockers.append("upload_failure_not_classified")

    return LambdaRemoteVSliceUploadFailureClassification(
        classification_status="classified" if not blockers else "blocked",
        failure_stage=failed_stage,
        source_bundle_upload_attempted=source_upload_attempted,
        source_bundle_upload_verified=source_upload_verified,
        dependency_bundle_upload_attempted=dependency_upload_attempted,
        manifest_started=bool(stage_results),
        tiny_smoke_attempted=tiny_smoke_attempted,
        raw_error_redacted=bool(evidence.get("stderr_secret_scan_passed", True)),
        redacted_error_summary=combined_error_text or None,
        failure_classification=failure_classification,
        decodilo_tested=decodilo_tested,
        no_training=not bool(report.get("training_attempted")),
        termination_verified=bool(report.get("termination_verified")),
        final_instance_count=post_summary.get("instance_count"),
        final_unmanaged_count=post_summary.get("unmanaged_count"),
        historical_billable_action_performed=bool(report.get("billable_action_performed")),
        blockers=blockers,
        warnings=[
            (
                "M073R failed before Decodilo tiny-smoke execution; "
                "this classification is offline-only"
            ),
        ],
    )


def load_lambda_upload_failure_classification(
    path: str | Path,
) -> LambdaRemoteVSliceUploadFailureClassification:
    return LambdaRemoteVSliceUploadFailureClassification.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_upload_failure_classification(
    path: str | Path,
    report: LambdaRemoteVSliceUploadFailureClassification,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
