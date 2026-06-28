"""Safe parser for tiny real-training smoke JSON artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.runtime_smoke_artifact_parser import DEFAULT_MAX_CONTENT_BYTES

TINY_REAL_TRAINING_SMOKE_DECLARED_ARTIFACT_PATH = (
    "/tmp/decodilo-tiny-real-training-smoke.json"
)

_SECRET_PATTERNS = [
    re.compile(r"Authorization:\s*[^,\"}\n]+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?:API|LAMBDA)[_-]?KEY\s*[:=]\s*(?!<|redacted)", re.IGNORECASE),
    re.compile(r"password\s*[:=]\s*(?!<|redacted)", re.IGNORECASE),
]

TinyRealTrainingArtifactParseStatus = Literal[
    "parsed_safe_tiny_real_training_smoke_artifact",
    "parsed_redacted_tiny_real_training_smoke_artifact",
    "metadata_only_oversized",
    "rejected_non_json",
    "artifact_missing",
    "artifact_path_not_file",
    "blocked_policy_not_defined",
]


class TinyRealTrainingArtifactParserReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M093R"
    parse_status: TinyRealTrainingArtifactParseStatus
    artifact_path: str
    declared_artifact_path: str = TINY_REAL_TRAINING_SMOKE_DECLARED_ARTIFACT_PATH
    artifact_exists: bool
    artifact_bytes: int | None = None
    artifact_sha256: str | None = None
    max_content_bytes: int = DEFAULT_MAX_CONTENT_BYTES
    artifact_type: str = "json"
    json_parse_succeeded: bool = False
    secret_scan_passed: bool | None = None
    raw_content_persist_allowed: bool = False
    raw_content_persisted: bool = False
    parsed_summary_persisted: bool = False
    safe_artifact_body: dict[str, Any] | None = None
    parsed_summary: dict[str, Any] | None = None
    redactions_applied: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> TinyRealTrainingArtifactParserReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("tiny real-training artifact parser must remain offline")
        if self.raw_content_persisted and not self.raw_content_persist_allowed:
            raise ValueError("raw content cannot be persisted unless allowed")
        if self.parsed_summary:
            if self.parsed_summary.get("real_model_training_claimed"):
                raise ValueError("tiny smoke cannot claim model-scale training")
            if self.parsed_summary.get("paper_scale_training_claimed"):
                raise ValueError("tiny smoke cannot claim paper-scale training")
            if self.parsed_summary.get("gpu_required"):
                raise ValueError("tiny smoke cannot require GPU")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in _SECRET_PATTERNS)


def _redact_string(value: str, redactions: list[str]) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        if pattern.search(redacted):
            redacted = pattern.sub("<redacted>", redacted)
            redactions.append(pattern.pattern)
    return redacted


def _safe_scalar(value: Any, redactions: list[str]) -> Any:
    if isinstance(value, str):
        return _redact_string(value, redactions)
    if isinstance(value, bool | int | float) or value is None:
        return value
    if isinstance(value, list):
        return [_safe_scalar(item, redactions) for item in value[:20]]
    if isinstance(value, dict):
        return {
            str(key): _safe_scalar(item, redactions)
            for key, item in list(value.items())[:20]
        }
    return str(value)[:512]


def _summary_from_body(body: dict[str, Any], redactions: list[str]) -> dict[str, Any]:
    allowed_keys = [
        "tiny_real_training_smoke_status",
        "command",
        "synthetic",
        "model",
        "steps_requested",
        "steps_completed",
        "optimizer",
        "cpu_only",
        "network_used",
        "package_install_attempted",
        "download_attempted",
        "dataset_download_attempted",
        "model_download_attempted",
        "training_attempted",
        "real_training_mechanics_exercised",
        "real_model_training_claimed",
        "paper_scale_training_claimed",
        "torch_required",
        "gpu_required",
        "background_process_started",
        "initial_loss",
        "final_loss",
        "loss_finite_check_passed",
        "parameter_update_check_passed",
        "gradient_check_passed",
        "optimizer_state_check_passed",
        "deterministic_replay_check_passed",
        "max_abs_error",
        "failed_check",
        "error_classification",
        "safe_error_message",
        "launch_ready",
        "launch_allowed",
        "skipped_checks",
        "elapsed_seconds",
    ]
    return {
        key: _safe_scalar(body[key], redactions)
        for key in allowed_keys
        if key in body
    }


def _policy_value(policy: Any, name: str, default: Any) -> Any:
    if isinstance(policy, dict):
        return policy.get(name, default)
    return getattr(policy, name, default)


def _load_policy(policy: str | Path | dict[str, Any] | Any) -> Any:
    if isinstance(policy, str | Path):
        return json.loads(Path(policy).read_text(encoding="utf-8"))
    return policy


def parse_tiny_real_training_artifact_file(
    *,
    artifact_path: str | Path,
    policy: str | Path | dict[str, Any] | Any,
) -> TinyRealTrainingArtifactParserReport:
    loaded_policy = _load_policy(policy)
    declared_path = str(
        _policy_value(
            loaded_policy,
            "declared_artifact_path",
            TINY_REAL_TRAINING_SMOKE_DECLARED_ARTIFACT_PATH,
        )
    )
    max_bytes = int(
        _policy_value(loaded_policy, "max_content_bytes", DEFAULT_MAX_CONTENT_BYTES)
    )
    if _policy_value(loaded_policy, "policy_status", "policy_defined") not in {
        "policy_defined",
        "manifest_artifact_policy_defined",
    }:
        return TinyRealTrainingArtifactParserReport(
            parse_status="blocked_policy_not_defined",
            artifact_path=str(artifact_path),
            declared_artifact_path=declared_path,
            artifact_exists=False,
            max_content_bytes=max_bytes,
            blockers=["manifest_artifact_policy_not_defined"],
        )
    path = Path(artifact_path)
    if not path.exists():
        return TinyRealTrainingArtifactParserReport(
            parse_status="artifact_missing",
            artifact_path=str(path),
            declared_artifact_path=declared_path,
            artifact_exists=False,
            max_content_bytes=max_bytes,
            blockers=["artifact_missing"],
        )
    if not path.is_file():
        return TinyRealTrainingArtifactParserReport(
            parse_status="artifact_path_not_file",
            artifact_path=str(path),
            declared_artifact_path=declared_path,
            artifact_exists=True,
            max_content_bytes=max_bytes,
            blockers=["artifact_path_not_file"],
        )
    size = path.stat().st_size
    sha256 = _sha256_file(path)
    if size > max_bytes:
        return TinyRealTrainingArtifactParserReport(
            parse_status="metadata_only_oversized",
            artifact_path=str(path),
            declared_artifact_path=declared_path,
            artifact_exists=True,
            artifact_bytes=size,
            artifact_sha256=sha256,
            max_content_bytes=max_bytes,
            warnings=["artifact_body_not_read_because_oversized"],
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    secret_scan_passed = not _contains_secret(text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return TinyRealTrainingArtifactParserReport(
            parse_status="rejected_non_json",
            artifact_path=str(path),
            declared_artifact_path=declared_path,
            artifact_exists=True,
            artifact_bytes=size,
            artifact_sha256=sha256,
            max_content_bytes=max_bytes,
            secret_scan_passed=secret_scan_passed,
            blockers=["artifact_json_parse_failed"],
        )
    if not isinstance(parsed, dict):
        return TinyRealTrainingArtifactParserReport(
            parse_status="rejected_non_json",
            artifact_path=str(path),
            declared_artifact_path=declared_path,
            artifact_exists=True,
            artifact_bytes=size,
            artifact_sha256=sha256,
            max_content_bytes=max_bytes,
            json_parse_succeeded=True,
            secret_scan_passed=secret_scan_passed,
            blockers=["artifact_json_root_not_object"],
        )
    redactions: list[str] = []
    summary = _summary_from_body(parsed, redactions)
    if secret_scan_passed:
        return TinyRealTrainingArtifactParserReport(
            parse_status="parsed_safe_tiny_real_training_smoke_artifact",
            artifact_path=str(path),
            declared_artifact_path=declared_path,
            artifact_exists=True,
            artifact_bytes=size,
            artifact_sha256=sha256,
            max_content_bytes=max_bytes,
            json_parse_succeeded=True,
            secret_scan_passed=True,
            raw_content_persist_allowed=True,
            raw_content_persisted=True,
            parsed_summary_persisted=bool(summary),
            safe_artifact_body=parsed,
            parsed_summary=summary or None,
        )
    return TinyRealTrainingArtifactParserReport(
        parse_status="parsed_redacted_tiny_real_training_smoke_artifact",
        artifact_path=str(path),
        declared_artifact_path=declared_path,
        artifact_exists=True,
        artifact_bytes=size,
        artifact_sha256=sha256,
        max_content_bytes=max_bytes,
        json_parse_succeeded=True,
        secret_scan_passed=False,
        raw_content_persist_allowed=False,
        raw_content_persisted=False,
        parsed_summary_persisted=bool(summary),
        parsed_summary=summary or None,
        redactions_applied=sorted(set(redactions)),
        warnings=["raw_artifact_body_not_persisted_due_to_secret_scan"],
    )


def load_tiny_real_training_artifact_parser_report(
    path: str | Path,
) -> TinyRealTrainingArtifactParserReport:
    return TinyRealTrainingArtifactParserReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_tiny_real_training_artifact_parser_report(
    path: str | Path,
    report: TinyRealTrainingArtifactParserReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
