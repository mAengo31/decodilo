"""M089R remote bounded synthetic DiLoCo experiment success record."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

M089R_REQUIRED_STAGES = (
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
    "bounded_diloco_experiment_command",
)
M089R_BOUNDED_DILOCO_ARTIFACT_PATH = "/tmp/decodilo-bounded-diloco-experiment.json"
M089R_BOUNDED_DILOCO_ARTIFACT_SHA256 = (
    "861c6c5a7debd9c769ff74454cdbd78aa9d9fb4da9d04b57d8d2968d551d6a8a"
)
M089R_BOUNDED_DILOCO_ARTIFACT_BYTES = 8254
M089R_SOURCE_BUNDLE_SHA256 = (
    "2ae45a852850695c933682e3750a9c572a306e2fbdc321014c403796ad5d8c80"
)
M068W_DEPENDENCY_BUNDLE_SHA256 = (
    "fd8037793220e53ce3583a7f44a16f6ca18696bcc3b13b27671f90e966a1ad22"
)

SECRET_PATTERNS = {
    "authorization_header": re.compile(r"Authorization:\s*\S+", re.IGNORECASE),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "provider_token": re.compile(r"lambda_[a-z0-9]{24,}", re.IGNORECASE),
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
}

LambdaBoundedDilocoExperimentSuccessStatus = Literal[
    "remote_bounded_synthetic_diloco_experiment_success",
    "remote_bounded_synthetic_diloco_experiment_partial",
    "remote_bounded_synthetic_diloco_experiment_failed",
]


class LambdaBoundedDilocoExperimentSuccessRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M090"
    success_status: LambdaBoundedDilocoExperimentSuccessStatus
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
    bounded_diloco_experiment_command_passed: bool
    bounded_diloco_experiment_status: str | None = None
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    learners_observed: int | None = None
    sync_rounds_completed: int | None = None
    fragments_observed: int | None = None
    learner_syncer_exchange_check_passed: bool | None = None
    update_or_commit_check_passed: bool | None = None
    pseudo_gradient_check_passed: bool | None = None
    inner_adamw_check_passed: bool | None = None
    outer_nesterov_check_passed: bool | None = None
    optimizer_state_roundtrip_check_passed: bool | None = None
    fragment_update_check_passed: bool | None = None
    fragment_merge_check_passed: bool | None = None
    fragment_reconstruction_check_passed: bool | None = None
    fragment_schedule_check_passed: bool | None = None
    replay_or_metric_check_passed: bool | None = None
    integrated_reference_check_passed: bool | None = None
    protocol_optimizer_link_check_passed: bool | None = None
    optimizer_fragment_link_check_passed: bool | None = None
    protocol_fragment_link_check_passed: bool | None = None
    max_abs_error: float | None = None
    full_diloco_training_claimed: bool | None = None
    real_model_training_claimed: bool | None = None
    true_model_fragment_claimed: bool | None = None
    overlap_semantics: str | None = None
    quantization_semantics: str | None = None
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
    no_arbitrary_file_reads: bool
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
    def _validate_offline_record(self) -> LambdaBoundedDilocoExperimentSuccessRecord:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M090 success record must remain offline and disabled")
        if (
            self.success_status
            == "remote_bounded_synthetic_diloco_experiment_success"
            and self.blockers
        ):
            raise ValueError("successful bounded experiment record cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_bounded_diloco_experiment_success_record_from_paths(
    *,
    workdir: str | Path,
) -> LambdaBoundedDilocoExperimentSuccessRecord:
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
        for stage in M089R_REQUIRED_STAGES
    }
    body = report.get("experiment_output_artifact_body_json") or {}
    summary = report.get("experiment_output_artifact_parsed_summary") or {}
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
    no_downloads = not _truthy_any(
        report, evidence, "download_attempted", "downloads_attempted"
    )
    no_training = not _truthy_any(
        report, evidence, "training_attempted", "real_model_training_attempted"
    )
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
    blockers: list[str] = [name for name, value in required_true.items() if not value]
    blockers.extend(
        f"{stage}_not_passed" for stage, value in passed.items() if not value
    )
    if artifact_path != M089R_BOUNDED_DILOCO_ARTIFACT_PATH:
        blockers.append("unexpected_bounded_diloco_artifact_path")
    if artifact_sha != M089R_BOUNDED_DILOCO_ARTIFACT_SHA256:
        blockers.append("unexpected_bounded_diloco_artifact_sha256")
    if artifact_bytes != M089R_BOUNDED_DILOCO_ARTIFACT_BYTES:
        blockers.append("unexpected_bounded_diloco_artifact_size")
    if _value(body, summary, "bounded_diloco_experiment_status") != "passed":
        blockers.append("bounded_diloco_experiment_status_not_passed")
    if _value(body, summary, "optimization_fidelity") not in {
        "bounded_synthetic_diloco_experiment",
        "partial_bounded_synthetic_diloco_experiment",
    }:
        blockers.append("optimization_fidelity_not_verified")
    if _value(body, summary, "inner_optimizer_semantics") != "adamw":
        blockers.append("inner_optimizer_semantics_not_adamw")
    if _value(body, summary, "outer_optimizer_semantics") != "nesterov":
        blockers.append("outer_optimizer_semantics_not_nesterov")
    if _value(body, summary, "parameter_fragment_semantics") != "synthetic_vector_fragments":
        blockers.append("parameter_fragment_semantics_not_synthetic_vector_fragments")
    for key, expected in {
        "learners_observed": 1,
        "sync_rounds_completed": 1,
        "fragments_observed": 2,
    }.items():
        if _int_value(_value(body, summary, key)) != expected:
            blockers.append(f"{key}_mismatch")
    for key in (
        "learner_syncer_exchange_check_passed",
        "update_or_commit_check_passed",
        "pseudo_gradient_check_passed",
        "inner_adamw_check_passed",
        "outer_nesterov_check_passed",
        "optimizer_state_roundtrip_check_passed",
        "fragment_update_check_passed",
        "fragment_merge_check_passed",
        "fragment_reconstruction_check_passed",
        "fragment_schedule_check_passed",
        "replay_or_metric_check_passed",
        "integrated_reference_check_passed",
        "protocol_optimizer_link_check_passed",
        "optimizer_fragment_link_check_passed",
        "protocol_fragment_link_check_passed",
    ):
        if _value(body, summary, key) is not True:
            blockers.append(f"{key}_not_passed")
    if _float_value(_value(body, summary, "max_abs_error")) != 0.0:
        blockers.append("max_abs_error_nonzero")
    if _value(body, summary, "full_diloco_training_claimed") is not False:
        blockers.append("full_diloco_training_claimed")
    if _value(body, summary, "real_model_training_claimed") is not False:
        blockers.append("real_model_training_claimed")
    if _value(body, summary, "true_model_fragment_claimed") is not False:
        blockers.append("true_model_fragment_claimed")
    if _value(body, summary, "overlap_semantics") != "not_exercised":
        blockers.append("overlap_semantics_overclaimed")
    if _value(body, summary, "quantization_semantics") != "not_exercised":
        blockers.append("quantization_semantics_overclaimed")
    if report.get("vertical_slice_status") != "vertical_slice_success":
        blockers.append("vertical_slice_not_success")
    if report.get("failed_stage") is not None:
        blockers.append("unexpected_failed_stage")
    if report.get("selected_candidate") != "gpu_1x_a10" or report.get(
        "selected_region"
    ) not in {"us-east-1", "us-west-1"}:
        blockers.append("selected_candidate_region_not_approved")
    if final_instance_count not in {0, None}:
        blockers.append("final_instance_count_nonzero")
    if final_unmanaged_count not in {0, None}:
        blockers.append("final_unmanaged_count_nonzero")
    if bool(post_summary.get("manual_review_required")):
        blockers.append("manual_review_required")
    if not no_internet_install:
        blockers.append("internet_install_detected")
    if not no_downloads:
        blockers.append("download_detected")
    if not no_training:
        blockers.append("real_training_detected")
    if not no_unapproved_transfer:
        blockers.append("unapproved_file_transfer_detected")

    if not blockers:
        status: LambdaBoundedDilocoExperimentSuccessStatus = (
            "remote_bounded_synthetic_diloco_experiment_success"
        )
    elif bool(report.get("launch_request_sent")):
        status = "remote_bounded_synthetic_diloco_experiment_partial"
    else:
        status = "remote_bounded_synthetic_diloco_experiment_failed"
    artifact_paths = _existing_artifact_paths(workdir_path, post_summary_path)
    artifact_hashes = {
        name: _sha256_file(Path(path)) for name, path in artifact_paths.items()
    }
    return LambdaBoundedDilocoExperimentSuccessRecord(
        success_status=status,
        run_id=str(report.get("run_id") or workdir_path.name),
        selected_candidate=report.get("selected_shape") or report.get("selected_candidate"),
        selected_region=report.get("selected_region"),
        source_bundle_sha256=(
            report.get("source_bundle_sha256")
            or evidence.get("source_bundle_sha256")
            or M089R_SOURCE_BUNDLE_SHA256
        ),
        dependency_bundle_sha256=(
            report.get("dependency_bundle_sha256")
            or evidence.get("dependency_bundle_sha256")
            or M068W_DEPENDENCY_BUNDLE_SHA256
        ),
        infrastructure_passed=not blockers,
        source_upload_passed=required_true["source_upload_passed"],
        dependency_upload_passed=required_true["dependency_upload_passed"],
        source_hash_verification_passed=required_true["source_hash_verification_passed"],
        dependency_hash_verification_passed=required_true[
            "dependency_hash_verification_passed"
        ],
        dependency_install_passed=required_true["dependency_install_passed"],
        decodilo_import_passed=passed["decodilo_import_check"],
        cli_help_passed=passed["decodilo_cli_help_check"],
        bounded_diloco_experiment_command_passed=passed[
            "bounded_diloco_experiment_command"
        ],
        bounded_diloco_experiment_status=_value(
            body, summary, "bounded_diloco_experiment_status"
        ),
        optimization_fidelity=_value(body, summary, "optimization_fidelity"),
        inner_optimizer_semantics=_value(body, summary, "inner_optimizer_semantics"),
        outer_optimizer_semantics=_value(body, summary, "outer_optimizer_semantics"),
        parameter_fragment_semantics=_value(
            body, summary, "parameter_fragment_semantics"
        ),
        learners_observed=_int_value(_value(body, summary, "learners_observed")),
        sync_rounds_completed=_int_value(
            _value(body, summary, "sync_rounds_completed")
        ),
        fragments_observed=_int_value(_value(body, summary, "fragments_observed")),
        learner_syncer_exchange_check_passed=_value(
            body, summary, "learner_syncer_exchange_check_passed"
        ),
        update_or_commit_check_passed=_value(
            body, summary, "update_or_commit_check_passed"
        ),
        pseudo_gradient_check_passed=_value(
            body, summary, "pseudo_gradient_check_passed"
        ),
        inner_adamw_check_passed=_value(body, summary, "inner_adamw_check_passed"),
        outer_nesterov_check_passed=_value(
            body, summary, "outer_nesterov_check_passed"
        ),
        optimizer_state_roundtrip_check_passed=_value(
            body, summary, "optimizer_state_roundtrip_check_passed"
        ),
        fragment_update_check_passed=_value(
            body, summary, "fragment_update_check_passed"
        ),
        fragment_merge_check_passed=_value(
            body, summary, "fragment_merge_check_passed"
        ),
        fragment_reconstruction_check_passed=_value(
            body, summary, "fragment_reconstruction_check_passed"
        ),
        fragment_schedule_check_passed=_value(
            body, summary, "fragment_schedule_check_passed"
        ),
        replay_or_metric_check_passed=_value(
            body, summary, "replay_or_metric_check_passed"
        ),
        integrated_reference_check_passed=_value(
            body, summary, "integrated_reference_check_passed"
        ),
        protocol_optimizer_link_check_passed=_value(
            body, summary, "protocol_optimizer_link_check_passed"
        ),
        optimizer_fragment_link_check_passed=_value(
            body, summary, "optimizer_fragment_link_check_passed"
        ),
        protocol_fragment_link_check_passed=_value(
            body, summary, "protocol_fragment_link_check_passed"
        ),
        max_abs_error=_float_value(_value(body, summary, "max_abs_error")),
        full_diloco_training_claimed=_value(
            body, summary, "full_diloco_training_claimed"
        ),
        real_model_training_claimed=_value(body, summary, "real_model_training_claimed"),
        true_model_fragment_claimed=_value(body, summary, "true_model_fragment_claimed"),
        overlap_semantics=_value(body, summary, "overlap_semantics"),
        quantization_semantics=_value(body, summary, "quantization_semantics"),
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
        no_arbitrary_file_reads=not _truthy_any(
            report, evidence, "arbitrary_file_read_attempted"
        ),
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
            "M090 records historical M089R billable work but performs no billable action",
            "M089R proves a bounded synthetic DiLoCo experiment only; it does not "
            "claim real training, paper-scale DiLoCo, true model fragments, overlap, "
            "or quantization",
        ],
    )


def load_lambda_bounded_diloco_experiment_success_record(
    path: str | Path,
) -> LambdaBoundedDilocoExperimentSuccessRecord:
    return LambdaBoundedDilocoExperimentSuccessRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_bounded_diloco_experiment_success_record(
    path: str | Path,
    record: LambdaBoundedDilocoExperimentSuccessRecord,
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


def _value(body: dict[str, Any], summary: dict[str, Any], key: str) -> Any:
    return body.get(key) if key in body else summary.get(key)


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return len(value)
    return None


def _float_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _find_clean_post_summary(workdir: Path) -> Path | None:
    local_candidates = [
        workdir / "post-discovery-summary-final.json",
        workdir / "final-discovery-summary.json",
        workdir / "post-discovery-summary.json",
    ]
    global_candidates = sorted(
        Path("/tmp").glob("decodilo-lambda-post-m089r-summary*.json"),
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
        "source_bundle": Path("/tmp/decodilo-source-bundle-m089r.tar.gz"),
        "dependency_bundle": Path("/tmp/decodilo-dependency-bundle-m068w.tar.gz"),
        "source_bundle_validation": Path(
            "/tmp/decodilo-lambda-m089r-source-bundle-validation.json"
        ),
        "dependency_bundle_validation": Path(
            "/tmp/decodilo-lambda-m089r-dependency-bundle-validation.json"
        ),
        "command_manifest": Path("/tmp/decodilo-lambda-m089r-command-manifest.json"),
        "manifest_validation": Path(
            "/tmp/decodilo-lambda-m089r-manifest-validation.json"
        ),
        "plan": Path("/tmp/decodilo-lambda-m089r-plan.json"),
        "gate_check": Path("/tmp/decodilo-lambda-m089r-gate-check.json"),
        "authorization": Path(
            "/tmp/decodilo-lambda-m089r-bounded-diloco-experiment-authorization.json"
        ),
        "runbook_preview": Path(
            "/tmp/decodilo-lambda-m089r-bounded-diloco-experiment-runbook-preview.json"
        ),
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
        if path is None or not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS.values()):
            return False
    return True
