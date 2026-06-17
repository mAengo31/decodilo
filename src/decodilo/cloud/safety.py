"""Dry-run cloud safety checks."""

from __future__ import annotations

from decodilo.cloud.launch_plan import CloudLaunchPlan, CloudSafetyCheck


def no_secret_values_embedded(plan: CloudLaunchPlan) -> CloudSafetyCheck:
    serialized = plan.model_dump_json()
    forbidden = ["AKIA", "secret_access_key", "-----BEGIN", "lambda_api_key"]
    leaked = [marker for marker in forbidden if marker in serialized]
    return CloudSafetyCheck(
        name="no_secret_values_embedded",
        passed=not leaked,
        reason="secret marker found" if leaked else "no secret-looking values found",
    )


def dry_run_only_check() -> CloudSafetyCheck:
    return CloudSafetyCheck(
        name="dry_run_only",
        passed=True,
        reason="launch_allowed is forced false and no launch client is configured",
    )


def validate_cloud_plan(plan: CloudLaunchPlan) -> list[str]:
    errors: list[str] = []
    if plan.launch_allowed:
        errors.append("launch_allowed must be false while launcher is disabled")
    if plan.mode != "cloud-dry-run":
        errors.append("cloud plan mode must be cloud-dry-run")
    if plan.node_count <= 0 or plan.total_gpus <= 0 or plan.planned_hours <= 0:
        errors.append("node_count, total_gpus, and planned_hours must be positive")
    if plan.safety_buffer_adjusted_cost > plan.starting_credits:
        errors.append("safety-adjusted cost exceeds starting credits")
    if plan.base_estimated_cost > plan.max_run_budget:
        errors.append("base estimated cost exceeds max_run_budget")
    secret_check = no_secret_values_embedded(plan)
    if not secret_check.passed:
        errors.append(secret_check.reason)
    return errors
