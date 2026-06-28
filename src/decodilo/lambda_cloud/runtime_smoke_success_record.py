"""M075R4 remote Decodilo runtime/protocol smoke success record."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

M075R4_REQUIRED_STAGES = (
    "python_version_check",
    "source_bundle_hash_check",
    "dependency_bundle_hash_check",
    "source_extract_dir",
    "source_bundle_extract",
    "dependency_extract_dir",
    "dependency_bundle_extract",
    "dependency_install_local_only",
    "decodilo_import_check",
    "decodilo_cli_help_check",
    "runtime_smoke_command",
)
M075R4_RUNTIME_SMOKE_ARTIFACT_PATH = "/tmp/decodilo-runtime-smoke.json"
M075R4_RUNTIME_SMOKE_ARTIFACT_SHA256 = (
    "361c2cf6b5d7f54ee5cdbdc5ac7b442f5f574d3882360c990784b3235e990519"
)
M075R4_RUNTIME_SMOKE_ARTIFACT_BYTES = 1520
M075R4_SOURCE_BUNDLE_SHA256 = (
    "5f5b2601810ee7d5e4b6e3fbaf82ede7b5ed237d4a63ab6b22d9e68da04d5d43"
)
M068W_DEPENDENCY_BUNDLE_SHA256 = (
    "fd8037793220e53ce3583a7f44a16f6ca18696bcc3b13b27671f90e966a1ad22"
)
SECRET_PATTERNS = {
    "authorization_header": re.compile(r"Authorization:\s*\S+", re.IGNORECASE),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "api_key_value": re.compile(r"API[_-]?KEY\s*[:=]\s*(?!<|redacted)", re.IGNORECASE),
    "password_value": re.compile(r"password\s*[:=]\s*(?!<|redacted)", re.IGNORECASE),
}

LambdaRuntimeSmokeSuccessStatus = Literal[
    "runtime_protocol_smoke_success",
    "runtime_protocol_smoke_partial",
    "runtime_protocol_smoke_failed",
]


class LambdaRuntimeSmokeSuccessRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M076"
    success_status: LambdaRuntimeSmokeSuccessStatus
    run_id: str | None = None
    selected_candidate: str | None = None
    selected_region: str | None = None
    source_bundle_sha256: str | None = None
    dependency_bundle_sha256: str | None = None
    infrastructure_passed: bool
    source_upload_passed: bool
    dependency_upload_passed: bool
    source_hash_verification_passed: bool
    dependency_hash_verification_passed: bool
    dependency_install_passed: bool
    decodilo_import_passed: bool
    cli_help_passed: bool
    runtime_smoke_command_passed: bool
    runtime_smoke_status: str | None = None
    protocol_or_event_check_passed: bool | None = None
    replay_or_metric_check_passed: bool | None = None
    artifact_path: str | None = None
    artifact_bytes: int | None = None
    artifact_sha256: str | None = None
    artifact_secret_scan_passed: bool
    artifact_body_persisted: bool
    parsed_summary_persisted: bool
    safe_json_body_persisted: bool
    artifact_bounded: bool
    vertical_slice_status: str | None = None
    failed_stage: str | None = None
    no_internet_install: bool
    no_downloads: bool
    no_real_training: bool
    no_unapproved_file_transfer: bool
    no_port_forwarding: bool
    termination_verified: bool
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    manual_review_required: bool
    mutating_operations: int | None = None
    historical_billable_action_performed: bool
    estimated_spend: float | None = None
    conservative_estimated_spend: float | None = None
    spend_under_budget: bool
    secret_scan_passed: bool
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_offline_record(self) -> LambdaRuntimeSmokeSuccessRecord:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M076 success record must remain offline and disabled")
        if self.success_status == "runtime_protocol_smoke_success" and self.blockers:
            raise ValueError("successful runtime-smoke record cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_runtime_smoke_success_record_from_paths(
    *,
    workdir: str | Path,
) -> LambdaRuntimeSmokeSuccessRecord:
    workdir_path = Path(workdir)
    report_path = workdir_path / "report.json"
    evidence_path = workdir_path / "remote-vslice-evidence.json"
    spend_path = workdir_path / "spend-audit.json"
    post_summary_path = _find_clean_post_summary(workdir_path)
    report = _read_json(report_path)
    evidence = _read_json(evidence_path) if evidence_path.exists() else {}
    spend_audit = _read_json(spend_path) if spend_path.exists() else {}
    post_summary = _read_json(post_summary_path) if post_summary_path else {}
    stage_map = _stage_map(report, evidence)
    passed = {
        stage: bool(stage_map.get(stage, {}).get("passed"))
        for stage in M075R4_REQUIRED_STAGES
    }

    body = report.get("experiment_output_artifact_body_json") or {}
    summary = report.get("experiment_output_artifact_parsed_summary") or {}
    runtime_status = body.get("runtime_smoke_status") or summary.get(
        "runtime_smoke_status"
    )
    protocol_check = body.get("protocol_or_event_check_passed")
    replay_check = body.get("replay_or_metric_check_passed")
    artifact_path = report.get("experiment_output_artifact_path") or evidence.get(
        "experiment_output_artifact_path"
    )
    artifact_bytes = _int_value(
        report.get("experiment_output_artifact_bytes")
        or evidence.get("experiment_output_artifact_bytes")
    )
    artifact_sha = report.get("experiment_output_artifact_sha256") or evidence.get(
        "experiment_output_artifact_sha256"
    )
    artifact_secret_scan = bool(
        report.get("experiment_output_artifact_secret_scan_passed")
        and evidence.get("experiment_output_artifact_secret_scan_passed", True)
    )
    body_persisted = bool(report.get("experiment_output_artifact_body_persisted"))
    summary_persisted = bool(
        report.get("experiment_output_artifact_parsed_summary_persisted")
    )
    no_downloads = not _truthy_any(report, evidence, "download_attempted", "downloads_attempted")
    no_training = not _truthy_any(report, evidence, "training_attempted")
    no_internet_install = not _truthy_any(
        report,
        evidence,
        "internet_install_attempted",
        "lambda_side_internet_used",
    )
    uploaded_bundles_count = _int_value(
        evidence.get("uploaded_bundles_count", report.get("uploaded_bundles_count"))
    )
    no_unapproved_transfer = (
        uploaded_bundles_count in {None, 2}
        and not _truthy_any(
            report,
            evidence,
            "unapproved_file_transfer_attempted",
            "extra_file_transfer_attempted",
        )
    )
    final_instance_count = _int_value(
        post_summary.get("instance_count", report.get("final_instance_count"))
    )
    final_unmanaged_count = _int_value(
        post_summary.get("unmanaged_count", report.get("final_unmanaged_count"))
    )
    estimated_spend = _float_value(report.get("estimated_spend"))
    conservative_spend = _float_value(
        spend_audit.get("conservative_estimated_spend")
        or spend_audit.get("conservative_spend_audit")
        or spend_audit.get("estimated_spend")
    )
    artifact_bounded = artifact_bytes is not None and artifact_bytes <= 64 * 1024
    secret_scan_passed = _secret_scan_paths(
        [report_path, evidence_path, spend_path, post_summary_path]
    )
    required_true = {
        "source_upload_passed": _truthy_any(
            report, evidence, "source_bundle_upload_succeeded", "source_upload_passed"
        ),
        "dependency_upload_passed": _truthy_any(
            report,
            evidence,
            "dependency_bundle_upload_succeeded",
            "dependency_upload_passed",
        ),
        "source_hash_verification_passed": _truthy_any(
            report,
            evidence,
            "source_bundle_hash_verified",
            "source_hash_verification_passed",
        ),
        "dependency_hash_verification_passed": _truthy_any(
            report,
            evidence,
            "dependency_bundle_hash_verified",
            "dependency_hash_verification_passed",
        ),
        "dependency_install_passed": _truthy_any(
            report,
            evidence,
            "local_dependency_install_succeeded",
            "local_only_dependency_install_passed",
        ),
        "termination_verified": bool(report.get("termination_verified")),
        "manual_review_clear": not bool(post_summary.get("manual_review_required")),
        "spend_under_budget": (
            estimated_spend is not None and estimated_spend < 50
        )
        or (conservative_spend is not None and conservative_spend < 50),
        "artifact_exists": bool(report.get("experiment_output_artifact_exists")),
        "artifact_secret_scan_passed": artifact_secret_scan,
        "artifact_body_persisted": body_persisted,
        "parsed_summary_persisted": summary_persisted,
        "artifact_bounded": artifact_bounded,
        "secret_scan_passed": secret_scan_passed,
    }
    blockers: list[str] = []
    for name, value in required_true.items():
        if not value:
            blockers.append(name)
    for stage, value in passed.items():
        if not value:
            blockers.append(f"{stage}_not_passed")
    if artifact_path != M075R4_RUNTIME_SMOKE_ARTIFACT_PATH:
        blockers.append("unexpected_runtime_smoke_artifact_path")
    if artifact_sha != M075R4_RUNTIME_SMOKE_ARTIFACT_SHA256:
        blockers.append("unexpected_runtime_smoke_artifact_sha256")
    if artifact_bytes != M075R4_RUNTIME_SMOKE_ARTIFACT_BYTES:
        blockers.append("unexpected_runtime_smoke_artifact_size")
    if runtime_status != "passed":
        blockers.append("runtime_smoke_status_not_passed")
    if protocol_check is not True:
        blockers.append("protocol_or_event_check_not_passed")
    if replay_check is not True:
        blockers.append("replay_or_metric_check_not_passed")
    if report.get("vertical_slice_status") != "vertical_slice_success":
        blockers.append("vertical_slice_not_success")
    if report.get("failed_stage") is not None:
        blockers.append("unexpected_failed_stage")
    if final_instance_count not in {0, None}:
        blockers.append("final_instance_count_nonzero")
    if final_unmanaged_count not in {0, None}:
        blockers.append("final_unmanaged_count_nonzero")
    if not no_internet_install:
        blockers.append("internet_install_detected")
    if not no_downloads:
        blockers.append("download_detected")
    if not no_training:
        blockers.append("real_training_detected")
    if not no_unapproved_transfer:
        blockers.append("unapproved_file_transfer_detected")

    status: LambdaRuntimeSmokeSuccessStatus
    if not blockers:
        status = "runtime_protocol_smoke_success"
    elif bool(report.get("launch_request_sent")):
        status = "runtime_protocol_smoke_partial"
    else:
        status = "runtime_protocol_smoke_failed"

    artifact_paths = _existing_artifact_paths(workdir_path, post_summary_path)
    artifact_hashes = {
        name: _sha256_file(Path(path)) for name, path in artifact_paths.items()
    }
    return LambdaRuntimeSmokeSuccessRecord(
        success_status=status,
        run_id=str(report.get("run_id") or workdir_path.name),
        selected_candidate=report.get("selected_shape") or report.get("selected_candidate"),
        selected_region=report.get("selected_region"),
        source_bundle_sha256=(
            report.get("source_bundle_sha256")
            or evidence.get("source_bundle_sha256")
            or M075R4_SOURCE_BUNDLE_SHA256
        ),
        dependency_bundle_sha256=(
            report.get("dependency_bundle_sha256")
            or evidence.get("dependency_bundle_sha256")
            or M068W_DEPENDENCY_BUNDLE_SHA256
        ),
        infrastructure_passed=not blockers
        or all(
            required_true[name]
            for name in (
                "source_upload_passed",
                "dependency_upload_passed",
                "dependency_install_passed",
                "termination_verified",
            )
        ),
        source_upload_passed=required_true["source_upload_passed"],
        dependency_upload_passed=required_true["dependency_upload_passed"],
        source_hash_verification_passed=required_true["source_hash_verification_passed"],
        dependency_hash_verification_passed=required_true[
            "dependency_hash_verification_passed"
        ],
        dependency_install_passed=required_true["dependency_install_passed"],
        decodilo_import_passed=passed["decodilo_import_check"],
        cli_help_passed=passed["decodilo_cli_help_check"],
        runtime_smoke_command_passed=passed["runtime_smoke_command"],
        runtime_smoke_status=runtime_status,
        protocol_or_event_check_passed=protocol_check,
        replay_or_metric_check_passed=replay_check,
        artifact_path=artifact_path,
        artifact_bytes=artifact_bytes,
        artifact_sha256=artifact_sha,
        artifact_secret_scan_passed=artifact_secret_scan,
        artifact_body_persisted=body_persisted,
        parsed_summary_persisted=summary_persisted,
        safe_json_body_persisted=body_persisted,
        artifact_bounded=artifact_bounded,
        vertical_slice_status=report.get("vertical_slice_status"),
        failed_stage=report.get("failed_stage"),
        no_internet_install=no_internet_install,
        no_downloads=no_downloads,
        no_real_training=no_training,
        no_unapproved_file_transfer=no_unapproved_transfer,
        no_port_forwarding=not _truthy_any(report, evidence, "port_forwarding_attempted"),
        termination_verified=required_true["termination_verified"],
        final_instance_count=final_instance_count,
        final_unmanaged_count=final_unmanaged_count,
        manual_review_required=bool(post_summary.get("manual_review_required")),
        mutating_operations=_int_value(report.get("mutating_operations")),
        historical_billable_action_performed=bool(report.get("billable_action_performed")),
        estimated_spend=estimated_spend,
        conservative_estimated_spend=conservative_spend,
        spend_under_budget=required_true["spend_under_budget"],
        secret_scan_passed=secret_scan_passed,
        artifact_hashes=artifact_hashes,
        artifact_paths=artifact_paths,
        blockers=sorted(set(blockers)),
        warnings=[
            "M076 records historical M075R4 billable work but performs no billable action",
        ],
    )


def load_lambda_runtime_smoke_success_record(
    path: str | Path,
) -> LambdaRuntimeSmokeSuccessRecord:
    return LambdaRuntimeSmokeSuccessRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_runtime_smoke_success_record(
    path: str | Path,
    record: LambdaRuntimeSmokeSuccessRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stage_map(report: dict[str, Any], evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    stages = evidence.get("stage_results") or report.get("remote_command_stage_results") or []
    return {stage.get("stage"): stage for stage in stages if isinstance(stage, dict)}


def _truthy_any(*items: Any) -> bool:
    dicts = [item for item in items if isinstance(item, dict)]
    keys = [item for item in items if isinstance(item, str)]
    return any(bool(data.get(key)) for data in dicts for key in keys)


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return len(value)
    return None


def _float_value(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _find_clean_post_summary(workdir: Path) -> Path | None:
    local_candidates = [
        workdir / "post-discovery-summary-final.json",
        workdir / "final-discovery-summary.json",
        workdir / "post-discovery-summary.json",
    ]
    global_candidates = sorted(
        Path("/tmp").glob("decodilo-lambda-post-m075r4-summary*.json"),
        key=lambda path: path.stat().st_mtime if path.exists() else 0,
        reverse=True,
    )
    candidates = [path for path in local_candidates if path.exists()]
    candidates.extend(global_candidates)
    return _first_clean_or_first_existing(candidates)


def _first_clean_or_first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        try:
            data = _read_json(path)
        except Exception:  # noqa: BLE001
            continue
        if data.get("instance_count") == 0 and data.get("unmanaged_count") == 0:
            return path
    return paths[0] if paths else None


def _existing_artifact_paths(workdir: Path, post_summary: Path | None) -> dict[str, str]:
    candidates = {
        "launch_report": workdir / "report.json",
        "remote_vslice_evidence": workdir / "remote-vslice-evidence.json",
        "spend_audit": workdir / "spend-audit.json",
        "post_discovery_summary": post_summary,
        "source_bundle": Path("/tmp/decodilo-source-bundle-m075r4.tar.gz"),
        "dependency_bundle": Path("/tmp/decodilo-dependency-bundle-m068w.tar.gz"),
        "source_bundle_validation": Path(
            "/tmp/decodilo-lambda-m075r4-source-bundle-validation.json"
        ),
        "dependency_bundle_validation": Path(
            "/tmp/decodilo-lambda-m075r4-dependency-bundle-validation.json"
        ),
        "command_manifest": Path("/tmp/decodilo-lambda-m075r4-command-manifest.json"),
        "manifest_validation": Path(
            "/tmp/decodilo-lambda-m075r4-manifest-validation.json"
        ),
        "plan": Path("/tmp/decodilo-lambda-m075r4-plan.json"),
        "gate_check": Path("/tmp/decodilo-lambda-m075r4-gate-check.json"),
    }
    return {
        name: str(path)
        for name, path in candidates.items()
        if isinstance(path, Path) and path.exists()
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _secret_scan_paths(paths: list[Path | None]) -> bool:
    for path in paths:
        if path is None or not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS.values()):
            return False
    return True
