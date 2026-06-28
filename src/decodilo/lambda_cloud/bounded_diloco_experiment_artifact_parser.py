"""Safe parser for bounded synthetic DiLoCo experiment JSON artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.runtime_smoke_artifact_parser import DEFAULT_MAX_CONTENT_BYTES

BOUNDED_DILOCO_EXPERIMENT_DECLARED_ARTIFACT_PATH = (
    "/tmp/decodilo-bounded-diloco-experiment.json"
)

_SECRET_PATTERNS = [
    re.compile(r"Authorization:\s*[^,\"}\n]+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?:API|LAMBDA)[_-]?KEY\s*[:=]\s*(?!<|redacted)", re.IGNORECASE),
    re.compile(r"password\s*[:=]\s*(?!<|redacted)", re.IGNORECASE),
]

BoundedDilocoExperimentArtifactParseStatus = Literal[
    "parsed_safe_bounded_diloco_experiment_artifact",
    "parsed_redacted_bounded_diloco_experiment_artifact",
    "metadata_only_oversized",
    "rejected_non_json",
    "artifact_missing",
    "artifact_path_not_file",
    "blocked_policy_not_defined",
]


class BoundedDilocoExperimentArtifactParserReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M089R"
    parse_status: BoundedDilocoExperimentArtifactParseStatus
    artifact_path: str
    declared_artifact_path: str = BOUNDED_DILOCO_EXPERIMENT_DECLARED_ARTIFACT_PATH
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
    def _validate_report(self) -> BoundedDilocoExperimentArtifactParserReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("bounded experiment artifact parser must remain offline")
        if self.raw_content_persisted and not self.raw_content_persist_allowed:
            raise ValueError("raw content cannot be persisted unless allowed")
        if self.parsed_summary:
            if self.parsed_summary.get("full_diloco_training_claimed"):
                raise ValueError("bounded experiment cannot claim full DiLoCo training")
            if self.parsed_summary.get("real_model_training_claimed"):
                raise ValueError("bounded experiment cannot claim real model training")
            if self.parsed_summary.get("true_model_fragment_claimed"):
                raise ValueError("bounded experiment cannot claim true model fragments")
            if self.parsed_summary.get("overlap_semantics") == "implemented":
                raise ValueError("bounded experiment cannot claim overlap semantics")
            if self.parsed_summary.get("quantization_semantics") == "implemented":
                raise ValueError("bounded experiment cannot claim quantization semantics")
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
        "bounded_diloco_experiment_status",
        "optimization_fidelity",
        "inner_optimizer_requested",
        "outer_optimizer_requested",
        "inner_optimizer_semantics",
        "outer_optimizer_semantics",
        "parameter_fragment_semantics",
        "synthetic",
        "learners_requested",
        "learners_observed",
        "sync_rounds_requested",
        "sync_rounds_completed",
        "fragments_requested",
        "fragments_observed",
        "max_steps",
        "learner_syncer_exchange_check_passed",
        "update_or_commit_check_passed",
        "quorum_or_acceptance_check_passed",
        "synthetic_updates_produced",
        "synthetic_updates_accepted",
        "synthetic_updates_rejected",
        "global_version_before",
        "global_version_after",
        "useful_synthetic_tokens",
        "stale_update_count",
        "duplicate_update_count",
        "pseudo_gradient_check_passed",
        "inner_adamw_check_passed",
        "outer_nesterov_check_passed",
        "optimizer_state_roundtrip_check_passed",
        "reference_value_check_passed",
        "fragment_count",
        "fragment_ids",
        "fragment_ranges",
        "fragment_shapes",
        "fragment_update_check_passed",
        "fragment_merge_check_passed",
        "fragment_reconstruction_check_passed",
        "fragment_schedule_check_passed",
        "fragment_state_roundtrip_check_passed",
        "per_fragment_reference_check_passed",
        "global_reference_check_passed",
        "protocol_optimizer_link_check_passed",
        "optimizer_fragment_link_check_passed",
        "protocol_fragment_link_check_passed",
        "integrated_reference_check_passed",
        "replay_or_metric_check_passed",
        "artifact_or_report_check_passed",
        "tolerance",
        "max_abs_error",
        "full_diloco_training_claimed",
        "real_model_training_claimed",
        "true_model_fragment_claimed",
        "overlap_semantics",
        "quantization_semantics",
        "failed_check",
        "error_classification",
        "safe_error_message",
        "network_used",
        "package_install_attempted",
        "download_attempted",
        "training_attempted",
        "real_model_training_attempted",
        "torch_required",
        "gpu_required",
        "background_process_started",
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


def parse_bounded_diloco_experiment_artifact_file(
    *,
    artifact_path: str | Path,
    policy: str | Path | dict[str, Any] | Any,
) -> BoundedDilocoExperimentArtifactParserReport:
    loaded_policy = _load_policy(policy)
    declared_path = str(
        _policy_value(
            loaded_policy,
            "declared_artifact_path",
            BOUNDED_DILOCO_EXPERIMENT_DECLARED_ARTIFACT_PATH,
        )
    )
    max_bytes = int(
        _policy_value(loaded_policy, "max_content_bytes", DEFAULT_MAX_CONTENT_BYTES)
    )
    if _policy_value(loaded_policy, "policy_status", "policy_defined") not in {
        "policy_defined",
        "manifest_artifact_policy_defined",
    }:
        return BoundedDilocoExperimentArtifactParserReport(
            parse_status="blocked_policy_not_defined",
            artifact_path=str(artifact_path),
            declared_artifact_path=declared_path,
            artifact_exists=False,
            max_content_bytes=max_bytes,
            blockers=["manifest_artifact_policy_not_defined"],
        )
    path = Path(artifact_path)
    if not path.exists():
        return BoundedDilocoExperimentArtifactParserReport(
            parse_status="artifact_missing",
            artifact_path=str(path),
            declared_artifact_path=declared_path,
            artifact_exists=False,
            max_content_bytes=max_bytes,
            blockers=["artifact_missing"],
        )
    if not path.is_file():
        return BoundedDilocoExperimentArtifactParserReport(
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
        return BoundedDilocoExperimentArtifactParserReport(
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
        return BoundedDilocoExperimentArtifactParserReport(
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
        return BoundedDilocoExperimentArtifactParserReport(
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
        return BoundedDilocoExperimentArtifactParserReport(
            parse_status="parsed_safe_bounded_diloco_experiment_artifact",
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
    return BoundedDilocoExperimentArtifactParserReport(
        parse_status="parsed_redacted_bounded_diloco_experiment_artifact",
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


def load_bounded_diloco_experiment_artifact_parser_report(
    path: str | Path,
) -> BoundedDilocoExperimentArtifactParserReport:
    return BoundedDilocoExperimentArtifactParserReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_bounded_diloco_experiment_artifact_parser_report(
    path: str | Path,
    report: BoundedDilocoExperimentArtifactParserReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
