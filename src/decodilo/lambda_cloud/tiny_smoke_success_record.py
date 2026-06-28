"""M073R2 remote Decodilo tiny-smoke success record."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

M073R2_REQUIRED_STAGES = (
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
    "tiny_smoke_command",
)
M073R2_TINY_SMOKE_ARTIFACT_PATH = "/tmp/decodilo-tiny-smoke.json"
M073R2_TINY_SMOKE_ARTIFACT_SHA256 = (
    "1bc4b2ff19be2c02795da41c74fe95193f5ed6dc638422fafa48746e0bb79c5e"
)
M073R2_TINY_SMOKE_ARTIFACT_BYTES = 991
M073R2_SOURCE_BUNDLE_SHA256 = (
    "bf008577af4bf50cc365cbcb623cd6051d35e8809163cd3796ea21e772842974"
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

LambdaTinySmokeSuccessStatus = Literal[
    "tiny_smoke_success",
    "tiny_smoke_partial",
    "tiny_smoke_failed",
]


class LambdaTinySmokeSuccessRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M074"
    status: LambdaTinySmokeSuccessStatus
    run_id: str | None = None
    selected_candidate: str | None = None
    selected_region: str | None = None
    source_bundle_sha256: str | None = None
    dependency_bundle_sha256: str | None = None
    source_upload_passed: bool
    dependency_upload_passed: bool
    source_hash_verification_passed: bool
    dependency_hash_verification_passed: bool
    local_only_dependency_install_passed: bool
    decodilo_import_passed: bool
    cli_help_passed: bool
    tiny_smoke_command_passed: bool
    tiny_smoke_artifact_created: bool
    artifact_path: str | None = None
    artifact_bytes: int | None = None
    artifact_sha256: str | None = None
    artifact_secret_scan_passed: bool
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
    def _validate_offline_record(self) -> LambdaTinySmokeSuccessRecord:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M074 success record must remain offline and disabled")
        if self.status == "tiny_smoke_success" and self.blockers:
            raise ValueError("successful tiny-smoke record cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_tiny_smoke_success_record_from_paths(
    *,
    workdir: str | Path,
) -> LambdaTinySmokeSuccessRecord:
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

    no_downloads = not _truthy_any(report, evidence, "download_attempted", "downloads_attempted")
    no_real_training = not _truthy_any(report, evidence, "training_attempted")
    no_internet_install = not _truthy_any(
        report,
        evidence,
        "internet_install_attempted",
        "internet_download_used",
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
    secret_scan_passed = _secret_scan_paths(
        [report_path, evidence_path, spend_path, post_summary_path]
    )

    passed = {
        stage: bool(stage_map.get(stage, {}).get("passed"))
        for stage in M073R2_REQUIRED_STAGES
    }
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
    artifact_created = bool(
        report.get("experiment_output_artifact_exists")
        and report.get("experiment_output_artifact_capture_succeeded")
    )
    artifact_secret_scan_passed = bool(
        report.get("experiment_output_artifact_secret_scan_passed")
        and evidence.get("experiment_output_artifact_secret_scan_passed", True)
    )
    artifact_bounded = artifact_bytes is not None and artifact_bytes <= 64 * 1024

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
        "local_only_dependency_install_passed": _truthy_any(
            report,
            evidence,
            "local_dependency_install_succeeded",
            "local_only_dependency_install_passed",
        ),
        "termination_verified": bool(report.get("termination_verified")),
        "manual_review_clear": not bool(report.get("manual_review_required")),
        "spend_under_budget": (
            estimated_spend is not None and estimated_spend < 50
        )
        or (conservative_spend is not None and conservative_spend < 50),
        "artifact_created": artifact_created,
        "artifact_secret_scan_passed": artifact_secret_scan_passed,
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
    if artifact_path != M073R2_TINY_SMOKE_ARTIFACT_PATH:
        blockers.append("unexpected_tiny_smoke_artifact_path")
    if artifact_sha != M073R2_TINY_SMOKE_ARTIFACT_SHA256:
        blockers.append("unexpected_tiny_smoke_artifact_sha256")
    if artifact_bytes != M073R2_TINY_SMOKE_ARTIFACT_BYTES:
        blockers.append("unexpected_tiny_smoke_artifact_size")
    if not no_internet_install:
        blockers.append("internet_install_detected")
    if not no_downloads:
        blockers.append("download_detected")
    if not no_real_training:
        blockers.append("real_training_detected")
    if not no_unapproved_transfer:
        blockers.append("unapproved_file_transfer_detected")
    if final_instance_count not in {0, None}:
        blockers.append("final_instance_count_nonzero")
    if final_unmanaged_count not in {0, None}:
        blockers.append("final_unmanaged_count_nonzero")
    if (
        report.get("vertical_slice_status") != "vertical_slice_success"
        or report.get("failed_stage") is not None
    ):
        blockers.append("vertical_slice_not_clean_success")

    status: LambdaTinySmokeSuccessStatus
    if not blockers:
        status = "tiny_smoke_success"
    elif any(passed.values()) or bool(report.get("launch_request_sent")):
        status = "tiny_smoke_partial"
    else:
        status = "tiny_smoke_failed"

    artifact_paths = _existing_artifact_paths(workdir_path, post_summary_path)
    artifact_hashes = {
        name: _sha256_file(Path(path)) for name, path in artifact_paths.items()
    }
    return LambdaTinySmokeSuccessRecord(
        status=status,
        run_id=str(report.get("run_id") or report.get("workdir") or workdir_path.name),
        selected_candidate=report.get("selected_shape") or report.get("selected_candidate"),
        selected_region=report.get("selected_region"),
        source_bundle_sha256=(
            report.get("source_bundle_sha256")
            or evidence.get("source_bundle_sha256")
            or M073R2_SOURCE_BUNDLE_SHA256
        ),
        dependency_bundle_sha256=(
            report.get("dependency_bundle_sha256")
            or evidence.get("dependency_bundle_sha256")
            or M068W_DEPENDENCY_BUNDLE_SHA256
        ),
        source_upload_passed=required_true["source_upload_passed"],
        dependency_upload_passed=required_true["dependency_upload_passed"],
        source_hash_verification_passed=required_true["source_hash_verification_passed"],
        dependency_hash_verification_passed=required_true[
            "dependency_hash_verification_passed"
        ],
        local_only_dependency_install_passed=required_true[
            "local_only_dependency_install_passed"
        ],
        decodilo_import_passed=passed["decodilo_import_check"],
        cli_help_passed=passed["decodilo_cli_help_check"],
        tiny_smoke_command_passed=passed["tiny_smoke_command"],
        tiny_smoke_artifact_created=artifact_created,
        artifact_path=artifact_path,
        artifact_bytes=artifact_bytes,
        artifact_sha256=artifact_sha,
        artifact_secret_scan_passed=artifact_secret_scan_passed,
        artifact_bounded=artifact_bounded,
        vertical_slice_status=report.get("vertical_slice_status"),
        failed_stage=report.get("failed_stage"),
        no_internet_install=no_internet_install,
        no_downloads=no_downloads,
        no_real_training=no_real_training,
        no_unapproved_file_transfer=no_unapproved_transfer,
        no_port_forwarding=not _truthy_any(report, evidence, "port_forwarding_attempted"),
        termination_verified=required_true["termination_verified"],
        final_instance_count=final_instance_count,
        final_unmanaged_count=final_unmanaged_count,
        manual_review_required=bool(report.get("manual_review_required")),
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
            "M074 records historical M073R2 billable work but performs no billable action",
        ],
    )


def load_lambda_tiny_smoke_success_record(path: str | Path) -> LambdaTinySmokeSuccessRecord:
    return LambdaTinySmokeSuccessRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_tiny_smoke_success_record(
    path: str | Path,
    record: LambdaTinySmokeSuccessRecord,
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
    global_candidates = [
        Path("/tmp/decodilo-lambda-post-m073r2-summary-final-3.json"),
        Path("/tmp/decodilo-lambda-post-m073r2-summary-final.json"),
        Path("/tmp/decodilo-lambda-post-m073r2-summary.json"),
    ]
    local_existing = [path for path in local_candidates if path.exists()]
    if local_existing:
        return _first_clean_or_first_existing(local_existing)
    global_existing = [path for path in global_candidates if path.exists()]
    return _first_clean_or_first_existing(global_existing)


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
        "m073r_upload_closeout": Path("/tmp/decodilo-lambda-m073r-upload-closeout.json"),
        "m073r2_authorization": Path("/tmp/decodilo-lambda-m073r2-authorization.json"),
        "m073r2_runbook_preview": Path("/tmp/decodilo-lambda-m073r2-runbook-preview.json"),
        "source_bundle": Path("/tmp/decodilo-source-bundle-m073r2.tar.gz"),
        "dependency_bundle": Path("/tmp/decodilo-dependency-bundle-m068w.tar.gz"),
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
