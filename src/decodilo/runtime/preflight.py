"""Local preflight validation for run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.cloud.lambda_api_preflight import collect_lambda_api_preflight_evidence
from decodilo.cloud.remote_backend_review_preflight import (
    collect_remote_backend_review_preflight,
)
from decodilo.runtime.artifact_manifest import (
    ArtifactManifest,
    validate_artifact_manifest,
)
from decodilo.runtime.metrics_validation import validate_report_payload
from decodilo.runtime.perf_characterization import load_performance_characterization
from decodilo.runtime.remote_backend_design_report import load_remote_backend_design_report
from decodilo.runtime.run_spec import load_run_spec
from decodilo.scaling.scaling_report import load_scaling_decision_report
from decodilo.storage.artifact_reference_audit import audit_artifact_references
from decodilo.storage.gc import plan_artifact_gc
from decodilo.storage.gc_safety import failed_gc_transactions
from decodilo.storage.lifecycle_policy import ArtifactRetentionPolicy
from decodilo.storage.reachability_graph_report import build_reachability_graph_report
from decodilo.storage.remote_backend_conformance import load_remote_backend_conformance_report
from decodilo.storage.remote_backend_evidence import load_remote_backend_evidence_package
from decodilo.storage.remote_backend_readiness import load_remote_backend_readiness_report
from decodilo.storage.remote_backend_requirements import load_remote_backend_requirements
from decodilo.storage.trash_lifecycle import inspect_trash
from decodilo.syncer.recovery_audit import validate_recovery_manifest_chain
from decodilo.syncer.recovery_manifest import load_recovery_manifest


class PreflightResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    preflight_passed: bool
    safety_checks_passed: bool
    artifact_checks_passed: bool
    budget_checks_passed: bool
    launch_review_passed: bool
    launch_ready: bool = False
    launch_allowed: bool = False
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_artifacts: list[str] = Field(default_factory=list)
    budget_summary: dict[str, Any] | None = None
    resource_limit_summary: dict[str, Any] = Field(default_factory=dict)
    scaling_summary: dict[str, Any] | None = None


def run_local_preflight(*, workdir: str | Path) -> PreflightResult:
    root = Path(workdir)
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []
    run_spec_path = root / "run_spec.json"
    artifact_path = root / "artifacts.json"
    report_path = root / "report.json"
    recovery_manifest_path = root / "recovery_manifest.json"
    artifact_errors: list[str] = []
    if not run_spec_path.exists():
        errors.append("missing run_spec.json")
    else:
        spec = load_run_spec(run_spec_path)
        checked.append(str(run_spec_path))
    if not artifact_path.exists():
        errors.append("missing artifacts.json")
    else:
        manifest = ArtifactManifest.model_validate_json(artifact_path.read_text(encoding="utf-8"))
        checked.append(str(artifact_path))
        artifact_errors = validate_artifact_manifest(manifest)
        errors.extend(artifact_errors)
        checked.extend(record.path for record in manifest.artifacts.values())
        audit = audit_artifact_references(root)
        if not audit.passed:
            errors.extend(f"artifact audit: {error}" for error in audit.errors)
            errors.extend(
                f"artifact audit: untracked artifact: {path}"
                for path in audit.untracked_artifacts
            )
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        checked.append(str(report_path))
        validation = validate_report_payload(report)
        if not validation.passed:
            errors.extend(validation.errors)
    else:
        warnings.append("report.json not present")
    resource_summary = {}
    if run_spec_path.exists():
        resource_summary = {
            "backpressure": spec.backpressure_settings,
            "checkpoint": spec.checkpoint_settings,
            "update_delivery": spec.update_delivery_settings,
            "payload_storage_mode": spec.payload_storage_mode,
            "checkpoint_storage_mode": spec.checkpoint_storage_mode,
            "merge_mode": spec.merge_mode,
            "global_update_storage_mode": spec.global_update_storage_mode,
            "artifact_root": spec.artifact_root,
            "chunk_store_root": spec.chunk_store_root,
            "inline_payload_max_bytes": spec.inline_payload_max_bytes,
            "chunk_size_bytes": spec.chunk_size_bytes,
            "tensor_artifact_codec": spec.tensor_artifact_codec,
            "fragment_artifact_codec": spec.fragment_artifact_codec,
            "checkpoint_artifact_codec": spec.checkpoint_artifact_codec,
            "artifact_backend": "local_filesystem",
            "remote_backend_enabled": False,
            "artifact_backend_contract": {
                "backend_type": "local_filesystem",
                "range_reads_supported": True,
                "remote_backend_enabled": False,
            },
            "out_of_core_merge_configured": (
                spec.merge_mode == "streaming_chunked"
                and spec.fragment_artifact_codec == "binary_v1"
            ),
            "max_working_bytes": spec.chunk_size_bytes * 5,
        }
        if not spec.backpressure_settings:
            warnings.append("runtime resource limits are minimal or missing from RunSpec")
        if report_path.exists() and spec.checkpoint_storage_mode in {"chunked", "dual"}:
            if not recovery_manifest_path.exists():
                errors.append("chunked completed run is missing recovery_manifest.json")
            else:
                try:
                    load_recovery_manifest(recovery_manifest_path)
                    checked.append(str(recovery_manifest_path))
                except Exception as exc:  # noqa: BLE001 - surface lifecycle failure
                    errors.append(f"invalid recovery_manifest.json: {exc}")
                chain = validate_recovery_manifest_chain(root)
                if not chain.passed:
                    errors.extend(f"recovery chain: {error}" for error in chain.errors)
        failed_transactions = failed_gc_transactions(root)
        if failed_transactions:
            errors.extend(f"failed gc transaction: {tx}" for tx in failed_transactions)
        if (root / "event_segments" / "segments_manifest.json").exists() and not (
            root / "replay_snapshot.json"
        ).exists():
            warnings.append("segmented run has no recent replay snapshot")
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            committed = int(report.get("metrics", {}).get("committed_sync_rounds", 0) or 0)
            if committed > 20 and not (root / "compact_report.json").exists():
                warnings.append("long run has no idempotency compaction report")
        try:
            gc_plan = plan_artifact_gc(
                workdir=root,
                policy=ArtifactRetentionPolicy(dry_run=True, allow_incomplete=True),
            )
            resource_summary["gc_dry_run"] = {
                "errors": gc_plan.errors,
                "artifacts_scanned": gc_plan.artifacts_scanned,
                "bytes_reclaimable": gc_plan.bytes_reclaimable,
            }
            if gc_plan.errors:
                warnings.extend(f"gc dry-run: {error}" for error in gc_plan.errors)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"gc dry-run unavailable: {exc}")
        perf_path = root / "perf_characterization.json"
        if not perf_path.exists():
            perf_candidates = sorted(root.rglob("perf_characterization.json"))
            perf_path = perf_candidates[-1] if perf_candidates else perf_path
        if perf_path.exists():
            try:
                perf_report = load_performance_characterization(perf_path)
                resource_summary["perf_characterization"] = {
                    "path": str(perf_path),
                    "top_components_by_wall_time": perf_report.bottlenecks[
                        "top_components_by_wall_time"
                    ],
                    "validation": perf_report.validation,
                }
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"perf characterization unreadable: {exc}")
        else:
            warnings.append("perf characterization report not present")
        lifecycle_path = root / "lifecycle_stress_report.json"
        if lifecycle_path.exists():
            try:
                lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
                resource_summary["lifecycle_stress"] = {
                    "path": str(lifecycle_path),
                    "cycles_completed": lifecycle.get("cycles_completed"),
                    "run_validate_passed": lifecycle.get("run_validate_passed"),
                    "artifact_audit_passed": lifecycle.get("artifact_audit_passed"),
                }
            except json.JSONDecodeError as exc:
                warnings.append(f"lifecycle stress report unreadable: {exc}")
        trash = inspect_trash(root)
        resource_summary["trash_cleanup"] = {
            "entries": len(trash.entries),
            "failed_transactions": [
                entry.transaction_id
                for entry in trash.entries
                if entry.transaction_state in {"failed", "applying", "aborted"}
            ],
        }
        if resource_summary["trash_cleanup"]["failed_transactions"]:
            warnings.append("trash contains failed or incomplete GC transactions")
        try:
            reachability = build_reachability_graph_report(workdir=root)
            resource_summary["reachability_graph"] = {
                "nodes": len(reachability.nodes),
                "edges": len(reachability.edges),
                "unreachable_nodes": len(reachability.unreachable_nodes),
                "unresolved_references": len(reachability.unresolved_references),
            }
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"reachability graph unavailable: {exc}")
        scaling_report_path = _find_scaling_report(root)
        if scaling_report_path is not None:
            try:
                scaling_report = load_scaling_decision_report(scaling_report_path)
                resource_summary["learner_scaling_report"] = {
                    "path": str(scaling_report_path),
                    "recommended_learner_count": scaling_report.recommended_learner_count,
                    "dominant_bottleneck": scaling_report.dominant_bottleneck,
                    "backend_design_targets": scaling_report.backend_design_targets,
                    "launch_ready": scaling_report.cloud_state["launch_ready"],
                    "launch_allowed": scaling_report.cloud_state["launch_allowed"],
                }
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"learner scaling report unreadable: {exc}")
        remote_requirements_path = root / "remote_backend_requirements.json"
        remote_design_path = root / "remote_backend_design_validation.json"
        remote_conformance_path = root / "remote_conformance.json"
        remote_readiness_path = root / "remote_backend_readiness.json"
        remote_evidence_path = root / "remote_backend_evidence_package.json"
        remote_summary: dict[str, Any] = {"remote_backend_enabled": False}
        if remote_requirements_path.exists():
            try:
                requirements = load_remote_backend_requirements(remote_requirements_path)
                remote_summary["requirements_path"] = str(remote_requirements_path)
                remote_summary["target_learner_count"] = requirements.target_learner_count
                remote_summary["stress_learner_count"] = requirements.stress_learner_count
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"remote backend requirements unreadable: {exc}")
        if remote_design_path.exists():
            try:
                design = load_remote_backend_design_report(remote_design_path)
                remote_summary["design_validation_path"] = str(remote_design_path)
                remote_summary["design_status"] = design.recommendation.design_status
                remote_summary["blockers"] = design.blockers
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"remote backend design validation unreadable: {exc}")
        if remote_conformance_path.exists():
            try:
                conformance = load_remote_backend_conformance_report(remote_conformance_path)
                remote_summary["conformance_path"] = str(remote_conformance_path)
                remote_summary["conformance_status"] = conformance.conformance_status
                remote_summary["conformance_passed"] = conformance.passed
                if conformance.passed:
                    warnings.append(
                        "simulator conformance is not production backend readiness"
                    )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"remote backend conformance unreadable: {exc}")
        if remote_readiness_path.exists():
            try:
                readiness = load_remote_backend_readiness_report(remote_readiness_path)
                remote_summary["readiness_path"] = str(remote_readiness_path)
                remote_summary["readiness_status"] = readiness.readiness_status.value
                remote_summary["readiness_blockers"] = readiness.blockers
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"remote backend readiness unreadable: {exc}")
        if remote_evidence_path.exists():
            try:
                evidence = load_remote_backend_evidence_package(remote_evidence_path)
                remote_summary["evidence_package_path"] = str(remote_evidence_path)
                remote_summary["evidence_completeness_score"] = (
                    evidence.manifest.evidence_completeness_score
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"remote backend evidence package unreadable: {exc}")
        review = collect_remote_backend_review_preflight(root=root)
        remote_summary["review_evidence"] = review["summary"]
        warnings.extend(review["warnings"])
        errors.extend(review["errors"])
        if len(remote_summary) > 1:
            resource_summary["remote_backend_design"] = remote_summary
        if _has_lambda_api_evidence(root):
            lambda_evidence = collect_lambda_api_preflight_evidence(root=root)
            resource_summary["lambda_api_boundary"] = lambda_evidence["summary"]
            warnings.extend(lambda_evidence["warnings"])
            errors.extend(lambda_evidence["errors"])
        expected_state_bytes = _expected_state_bytes(spec.trainer_config)
        if expected_state_bytes is not None:
            resource_summary["expected_model_state_bytes"] = expected_state_bytes
        large_state_requested = (
            spec.require_chunked_for_large_state
            or (
                expected_state_bytes is not None
                and expected_state_bytes > spec.inline_payload_max_bytes
            )
        )
        if large_state_requested:
            if spec.payload_storage_mode == "inline":
                errors.append("large expected state requires chunked or auto payload storage")
            if spec.global_update_storage_mode == "inline":
                errors.append("large expected state requires chunked or auto global updates")
            if spec.checkpoint_storage_mode == "inline":
                errors.append("large expected state requires chunked or dual checkpoints")
            if spec.merge_mode == "in_memory":
                warnings.append(
                    "large expected state should use streaming_chunked merge "
                    "with out-of-core capability or document why not"
                )
            if "memory_budget_mb" not in spec.backpressure_settings:
                warnings.append("large expected state should include memory budget settings")
            if not spec.artifact_root:
                warnings.append("large expected state should configure artifact_root explicitly")
            if not spec.chunk_store_root:
                warnings.append("large expected state should configure chunk_store_root explicitly")
            if spec.tensor_artifact_codec == "json_safe":
                warnings.append("large expected state should use tensor_artifact_codec=binary_v1")
            if spec.fragment_artifact_codec == "json_safe":
                warnings.append("large expected state should use fragment_artifact_codec=binary_v1")
            if spec.checkpoint_artifact_codec == "json_safe":
                warnings.append(
                    "large expected state should use checkpoint_artifact_codec=binary_v1"
                )
    preflight_passed = not errors
    artifact_checks_passed = (
        not artifact_errors
        and run_spec_path.exists()
        and artifact_path.exists()
    )
    return PreflightResult(
        preflight_passed=preflight_passed,
        safety_checks_passed=preflight_passed,
        artifact_checks_passed=artifact_checks_passed,
        budget_checks_passed=True,
        launch_review_passed=False,
        launch_ready=False,
        launch_allowed=False,
        passed=preflight_passed,
        errors=errors,
        warnings=warnings,
        checked_artifacts=checked,
        budget_summary=None,
        resource_limit_summary=resource_summary,
    )


def _find_scaling_report(root: Path) -> Path | None:
    names = [
        "learner_scaling_report.json",
        "pod_optimization.json",
        "scaling_report.json",
        "learner-sweep.json",
    ]
    for name in names:
        candidate = root / name
        if candidate.exists():
            return candidate
    matches = sorted(root.rglob("*scaling*.json"))
    for match in matches:
        try:
            load_scaling_decision_report(match)
        except Exception:  # noqa: BLE001
            continue
        return match
    return None


def _has_lambda_api_evidence(root: Path) -> bool:
    names = {
        "lambda-discovery.json",
        "lambda-ledger.json",
        "lambda-preflight.json",
        "lambda-launch-plan.json",
        "lambda-teardown-plan.json",
        "lambda-m026-decision.json",
        "lambda-m027-authorization.json",
        "lambda-blocker-matrix.json",
        "lambda-evidence-freshness.json",
        "lambda-minimal-mutation-preflight.json",
        "lambda-minimal-mutation-audit.json",
        "lambda-m028-state-snapshot.json",
        "lambda-m028-budget-lock.json",
        "lambda-m028-resource-lock.json",
        "lambda-m028-no-mutation-audit.json",
        "lambda-m029-authorization.json",
        "lambda-m028-decision.json",
        "lambda-m028-report.json",
        "lambda-m029-report.json",
        "lambda-m029-spend-audit.json",
        "lambda-m029-ledger.json",
    }
    return any((root / name).exists() for name in names)


def _expected_state_bytes(trainer_config: dict[str, Any]) -> int | None:
    explicit = trainer_config.get("expected_model_state_bytes")
    if explicit is not None:
        return int(explicit)
    params = trainer_config.get("parameter_count") or trainer_config.get("params")
    bytes_per_param = trainer_config.get("bytes_per_parameter") or trainer_config.get(
        "bytes_per_param"
    )
    if params is None or bytes_per_param is None:
        return None
    return int(params) * int(bytes_per_param)
