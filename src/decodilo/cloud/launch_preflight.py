"""Cloud dry-run preflight gate. This is not a launcher."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from decodilo.cloud.lambda_api_preflight import collect_lambda_api_preflight_evidence
from decodilo.cloud.launch_plan import load_cloud_dry_run_report
from decodilo.cloud.launch_review import load_launch_review_checklist
from decodilo.cloud.remote_backend_preflight import collect_remote_backend_preflight_evidence
from decodilo.cloud.safety import validate_cloud_plan
from decodilo.runtime.preflight import PreflightResult, run_local_preflight
from decodilo.scaling.scaling_report import load_scaling_decision_report


def run_cloud_preflight(
    *,
    dry_run_plan: str | Path,
    workdir: str | Path | None = None,
    launch_review_path: str | Path | None = None,
) -> PreflightResult:
    report = load_cloud_dry_run_report(dry_run_plan)
    plan = report.plan
    safety_errors = [*report.validation_errors, *validate_cloud_plan(plan)]
    errors = list(safety_errors)
    warnings = list(plan.warnings)
    if "cloud launch is disabled in this build" not in warnings:
        warnings.append("cloud launch is disabled in this build")
    if "shared filesystem artifact transport only; no remote artifact backend" not in warnings:
        warnings.append("shared filesystem artifact transport only; no remote artifact backend")
    if "remote artifact backend is disabled in this build" not in warnings:
        warnings.append("remote artifact backend is disabled in this build")
    if "local retention policy is not a cloud retention policy" not in warnings:
        warnings.append("local retention policy is not a cloud retention policy")
    if "local perf numbers are not cloud performance guarantees" not in warnings:
        warnings.append("local perf numbers are not cloud performance guarantees")
    if "no accelerator characterization for target shape" not in warnings:
        warnings.append("no accelerator characterization for target shape")
    if "scaling model is heuristic unless calibrated" not in warnings:
        warnings.append("scaling model is heuristic unless calibrated")
    checked = [str(dry_run_plan)]
    if plan.launch_allowed:
        errors.append("launch_allowed must remain false")
    if plan.teardown_plan is None:
        errors.append("missing teardown_plan")
    else:
        checked.append("teardown_plan:inline")
        if plan.teardown_plan.get("has_live_resource_ids") or plan.teardown_plan.get(
            "live_resource_ids"
        ):
            errors.append("dry-run teardown plan must not contain live resource IDs")
    review_path = Path(launch_review_path) if launch_review_path else Path(dry_run_plan).with_name(
        "launch-review.json"
    )
    checklist = None
    if review_path.exists():
        checklist = load_launch_review_checklist(review_path)
        checked.append(str(review_path))
        if checklist.launch_allowed:
            errors.append("launch review must keep launch_allowed=false")
        if checklist.teardown_plan is None:
            errors.append("launch review missing teardown plan")
    else:
        errors.append("missing launch review checklist")
    budget_errors: list[str] = []
    if plan.budget_manifest is None:
        budget_errors.append("missing budget manifest")
        errors.append("missing budget manifest")
    if not plan.price_snapshot_id or not plan.selected_price_record_id:
        errors.append("dry-run plan must identify snapshot_id and record_id")
    if plan.capacity_plan is None:
        warnings.append("scaling estimates are missing from cloud-intended dry-run plan")
    if plan.expected_trainer_state_bytes is not None and workdir is None:
        warnings.append(
            "large expected state cannot be checked for chunked runtime modes without workdir"
        )
    artifact_checks_passed = True
    backend_targets: dict[str, Any] | None = None
    if workdir is not None:
        local = run_local_preflight(workdir=workdir)
        checked.extend(local.checked_artifacts)
        errors.extend(f"local: {error}" for error in local.errors)
        warnings.extend(f"local: {warning}" for warning in local.warnings)
        artifact_checks_passed = local.artifact_checks_passed
        scaling_resource = local.resource_limit_summary.get("learner_scaling_report")
        if scaling_resource is not None:
            backend_targets = scaling_resource.get("backend_design_targets")
    if backend_targets is None:
        report_path = Path(dry_run_plan).with_name("learner_scaling_report.json")
        if report_path.exists():
            try:
                scaling_report = load_scaling_decision_report(report_path)
                backend_targets = scaling_report.backend_design_targets
                checked.append(str(report_path))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"learner scaling report unreadable: {exc}")
    if backend_targets is None:
        warnings.append("learner scaling report missing for cloud-intended plan")
    remote_backend_evidence: dict[str, Any] | None = None
    lambda_api_evidence: dict[str, Any] | None = None
    if workdir is not None:
        evidence = collect_remote_backend_preflight_evidence(root=workdir)
        remote_backend_evidence = evidence["summary"]
        warnings.extend(evidence["warnings"])
        errors.extend(evidence["errors"])
        lambda_evidence = collect_lambda_api_preflight_evidence(root=workdir)
        lambda_api_evidence = lambda_evidence["summary"]
        warnings.extend(lambda_evidence["warnings"])
        errors.extend(lambda_evidence["errors"])
    else:
        warnings.append("remote backend evidence cannot be checked without workdir")
        warnings.append("Lambda API boundary evidence cannot be checked without workdir")
    budget_summary: dict[str, Any] | None = None
    if plan.budget_manifest is not None:
        budget_summary = {
            "base_estimated_cost": plan.base_estimated_cost,
            "safety_buffer_adjusted_cost": plan.safety_buffer_adjusted_cost,
            "projected_remaining_credits": plan.projected_remaining_credits,
            "max_run_budget": plan.max_run_budget,
        }
    safety_checks_passed = (
        not safety_errors
        and not plan.launch_allowed
        and plan.teardown_plan is not None
    )
    budget_checks_passed = not budget_errors and plan.budget_manifest is not None
    launch_review_passed = bool(checklist is not None and checklist.passed)
    preflight_passed = not errors
    return PreflightResult(
        preflight_passed=preflight_passed,
        safety_checks_passed=safety_checks_passed,
        artifact_checks_passed=artifact_checks_passed,
        budget_checks_passed=budget_checks_passed,
        launch_review_passed=launch_review_passed,
        launch_ready=False,
        launch_allowed=False,
        passed=preflight_passed,
        errors=errors,
        warnings=warnings,
        checked_artifacts=checked,
        budget_summary=budget_summary,
        resource_limit_summary={
            "node_count": plan.node_count,
            "total_gpus": plan.total_gpus,
            "planned_hours": plan.planned_hours,
            "artifact_backend": "local_filesystem",
            "remote_backend_enabled": False,
            "artifact_backend_contract": {
                "backend_type": "local_filesystem",
                "range_reads_supported": True,
                "remote_backend_enabled": False,
            },
            "out_of_core_merge_configured": False,
            "max_working_bytes": None,
            "backend_design_targets": backend_targets,
            "remote_backend_evidence": remote_backend_evidence,
            "lambda_api_evidence": lambda_api_evidence,
        },
        scaling_summary=plan.capacity_plan,
    )


def write_preflight_result(path: str | Path, result: PreflightResult) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
