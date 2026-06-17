"""Lambda dry-run planner with no API calls."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from decodilo.cloud.lambda_shapes import LambdaShapeCatalog
from decodilo.cloud.launch_plan import (
    CloudDryRunReport,
    CloudLaunchPlan,
    CloudNodePlan,
    CloudSafetyCheck,
)
from decodilo.cloud.safety import dry_run_only_check, no_secret_values_embedded, validate_cloud_plan
from decodilo.cloud.teardown_plan import build_dry_run_teardown_plan
from decodilo.pricing.budget import BudgetGuard, build_run_budget_manifest, hourly_cost_for_cluster
from decodilo.pricing.freshness import require_usable_snapshot
from decodilo.pricing.registry import load_price_snapshot, query_snapshot_price
from decodilo.runtime.run_spec import load_run_spec
from decodilo.scaling.capacity_plan import build_capacity_plan


class LambdaDryRunPlanner:
    """Build auditable Lambda cloud-dry-run plans without launching resources."""

    def __init__(self, *, shape_catalog: LambdaShapeCatalog | None = None) -> None:
        self.shape_catalog = shape_catalog or LambdaShapeCatalog()

    def build_plan(
        self,
        *,
        run_id: str,
        price_snapshot_path: str | Path,
        gpu_type: str,
        gpus_per_instance: int,
        nodes: int,
        hours: float,
        credits: float,
        max_run_budget: float,
        region: str | None = None,
        run_spec_path: str | Path | None = None,
        allow_sample_prices: bool = False,
        allow_stale_prices: bool = False,
        max_price_age_days: int = 7,
        safety_buffer_percentage: float = 0.15,
        instance_type: str | None = None,
        allow_ambiguous_price: bool = False,
        params: int | None = None,
        bytes_per_param: float | None = None,
        expected_tokens_per_second: float | None = None,
        expected_goodput: float | None = None,
        sync_interval_steps: int = 500,
        local_step_seconds: float = 1.0,
        compression_bits: int | None = None,
        num_learners: int | None = None,
    ) -> CloudDryRunReport:
        snapshot = load_price_snapshot(price_snapshot_path)
        require_usable_snapshot(
            snapshot,
            allow_sample_prices=allow_sample_prices,
            allow_stale_prices=allow_stale_prices,
            max_price_age_days=max_price_age_days,
        )
        shape = self.shape_catalog.lookup(
            gpu_type=gpu_type,
            gpus_per_instance=gpus_per_instance,
            shape=instance_type,
        )
        record = query_snapshot_price(
            snapshot,
            gpu_type=gpu_type,
            gpus_per_instance=gpus_per_instance,
            instance_type=instance_type,
            allow_ambiguous_price=allow_ambiguous_price,
        )
        price = record.to_price_profile()
        base_cost = hourly_cost_for_cluster(nodes, price) * hours
        guard = BudgetGuard(
            starting_credits=credits,
            safety_buffer_pct=safety_buffer_percentage,
        )
        decision = guard.require_run_allowed(
            estimated_run_cost=base_cost,
            max_run_budget=max_run_budget,
        )
        budget_manifest = build_run_budget_manifest(
            run_id=run_id,
            provider="lambda",
            mode="cloud-dry-run",
            price_snapshot_id=snapshot.snapshot_id,
            selected_price_record_ids=[record.record_id],
            planned_instances=nodes,
            gpus_per_instance=gpus_per_instance,
            planned_hours=hours,
            base_estimated_cost=base_cost,
            safety_buffer_percentage=safety_buffer_percentage,
            safety_buffer_adjusted_cost=decision.safety_buffer_adjusted_cost,
            max_run_budget=max_run_budget,
            starting_credits=credits,
            projected_remaining_credits=decision.projected_remaining_credits,
            allow_sample_prices=allow_sample_prices,
            allow_stale_prices=allow_stale_prices,
            notes="cloud dry-run only; no Lambda API calls or launches",
        )
        run_spec_hash = None
        run_spec = None
        if run_spec_path is not None:
            run_spec = load_run_spec(run_spec_path)
            run_spec_hash = run_spec.sha256()
        capacity_plan: dict[str, Any] | None = None
        warnings: list[str] = [
            "live Lambda availability is not checked",
            "cloud launch is disabled in this scaffold",
            "no Lambda API client is configured",
            "teardown is not verified because no live resources exist",
        ]
        if (
            params is not None
            and bytes_per_param is not None
            and expected_tokens_per_second is not None
            and expected_goodput is not None
        ):
            capacity = build_capacity_plan(
                price_record=record,
                num_instances=nodes,
                planned_hours=hours,
                parameter_count=params,
                bytes_per_parameter=bytes_per_param,
                num_learners=num_learners or nodes,
                expected_tokens_per_second=expected_tokens_per_second,
                expected_goodput=expected_goodput,
                credit_budget=credits,
                sync_interval_steps=sync_interval_steps,
                local_step_seconds=local_step_seconds,
            )
            capacity_dict = capacity.to_dict()
            if compression_bits is not None:
                from decodilo.scaling.bandwidth import estimate_outer_loop_bandwidth

                capacity_dict["bandwidth"] = estimate_outer_loop_bandwidth(
                    parameter_count=params,
                    bytes_per_parameter=bytes_per_param,
                    num_learners=num_learners or nodes,
                    num_fragments=128,
                    sync_interval_steps=sync_interval_steps,
                    local_step_seconds=local_step_seconds,
                    compression_bits=compression_bits,
                ).to_dict()
            capacity_plan = capacity_dict
            warnings.extend(capacity.warnings)
        safety_checks = [
            CloudSafetyCheck(name="fresh_price_snapshot", passed=True),
            CloudSafetyCheck(name="sample_price_policy", passed=True),
            CloudSafetyCheck(name="budget_guard", passed=True, reason=decision.reason),
            CloudSafetyCheck(name="positive_runtime", passed=hours > 0),
            CloudSafetyCheck(name="positive_nodes", passed=nodes > 0),
            CloudSafetyCheck(name="positive_gpus", passed=nodes * gpus_per_instance > 0),
            CloudSafetyCheck(name="localhost_default", passed=True),
            CloudSafetyCheck(name="no_api_client_configured", passed=True),
            dry_run_only_check(),
        ]
        teardown_plan = build_dry_run_teardown_plan(
            provider="lambda",
            run_id=run_id,
            resources_planned=[
                f"{nodes}x {shape.shape}",
                f"{nodes * gpus_per_instance} total {gpu_type} GPUs",
            ],
            max_runtime_hours=hours,
        )
        expected_model_parameter_count = params or (run_spec.vector_dim if run_spec else None)
        expected_trainer_state_bytes = (
            int(params * bytes_per_param)
            if params is not None and bytes_per_param is not None
            else None
        )
        launch_plan = CloudLaunchPlan(
            run_id=run_id,
            provider="lambda",
            region=region,
            node_count=nodes,
            instance_type=record.instance_type or shape.shape,
            gpu_type=gpu_type,
            gpus_per_instance=gpus_per_instance,
            total_gpus=nodes * gpus_per_instance,
            planned_hours=hours,
            price_snapshot_id=snapshot.snapshot_id,
            selected_price_record_id=record.record_id,
            base_estimated_cost=base_cost,
            safety_buffer_adjusted_cost=decision.safety_buffer_adjusted_cost,
            max_run_budget=max_run_budget,
            starting_credits=credits,
            projected_remaining_credits=decision.projected_remaining_credits,
            run_spec_hash=run_spec_hash,
            secrets_required=["LAMBDA_API_KEY"],
            startup_commands=[
                "echo dry-run-only: future launcher will start syncer and learners here"
            ],
            teardown_commands=["echo dry-run-only: future launcher will terminate nodes here"],
            teardown_plan=teardown_plan.model_dump(mode="json"),
            nodes=[
                CloudNodePlan(
                    node_id=f"lambda-node-{index}",
                    provider="lambda",
                    shape=shape.shape,
                    gpu_type=gpu_type,
                    gpus_per_instance=gpus_per_instance,
                    region=region,
                )
                for index in range(nodes)
            ],
            safety_checks=safety_checks,
            launch_allowed=False,
            reason_launch_not_allowed=(
                "This scaffold is cloud dry-run only; Lambda API calls and launches are disabled."
            ),
            budget_manifest=budget_manifest.model_dump(mode="json"),
            capacity_plan=capacity_plan,
            trainer_type=run_spec.trainer_type if run_spec else None,
            expected_trainer_state_bytes=expected_trainer_state_bytes,
            expected_model_parameter_count=expected_model_parameter_count,
            warnings=warnings,
        )
        safety_checks = [*launch_plan.safety_checks, no_secret_values_embedded(launch_plan)]
        launch_plan = launch_plan.model_copy(update={"safety_checks": safety_checks})
        return CloudDryRunReport(
            plan=launch_plan,
            validation_errors=validate_cloud_plan(launch_plan),
        )
