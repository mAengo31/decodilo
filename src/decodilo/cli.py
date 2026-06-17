"""Command line interface for the DecoDiLo scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.dry_run import validate_report as validate_cloud_dry_run_report
from decodilo.cloud.dry_run import write_report as write_cloud_dry_run_report
from decodilo.cloud.lambda_plan import LambdaDryRunPlanner
from decodilo.cloud.launch_plan import load_cloud_dry_run_report
from decodilo.cloud.launch_preflight import run_cloud_preflight, write_preflight_result
from decodilo.cloud.launch_review import (
    build_launch_review_checklist,
    write_launch_review_checklist,
)
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError
from decodilo.pricing.budget import (
    BudgetGuard,
    build_run_budget_manifest,
    hourly_cost_for_cluster,
)
from decodilo.pricing.freshness import require_usable_snapshot
from decodilo.pricing.lambda_prices import (
    get_price,
    load_lambda_prices_from_json,
    parse_lambda_pricing_html,
)
from decodilo.pricing.registry import (
    import_html_snapshot,
    import_json_snapshot,
    load_price_snapshot,
    query_snapshot_price,
)
from decodilo.pricing.snapshots import PriceSourceType
from decodilo.runtime import learner_worker, local_runner, syncer_service
from decodilo.runtime.artifact_manifest import (
    ArtifactManifest,
    build_artifact_manifest,
    validate_artifact_manifest,
    write_artifact_manifest,
)
from decodilo.runtime.fault_matrix import run_fault_matrix
from decodilo.runtime.lifecycle_stress import run_lifecycle_stress
from decodilo.runtime.local_runner import LocalRunConfig
from decodilo.runtime.metrics_validation import validate_report_payload
from decodilo.runtime.perf_baselines import (
    run_artifact_io_baseline,
    run_compare_codecs,
    run_merge_benchmark,
)
from decodilo.runtime.perf_harness import run_local_overhead_harness
from decodilo.runtime.preflight import run_local_preflight
from decodilo.runtime.run_lifecycle import (
    compact_run,
    inspect_run,
    refresh_lifecycle_artifact_manifest,
    validate_run,
)
from decodilo.runtime.soak import run_local_soak
from decodilo.runtime.soak_profiles import get_soak_profile
from decodilo.runtime.trainer_matrix import list_trainers, run_trainer_check, run_trainer_matrix
from decodilo.scaling.bandwidth import estimate_outer_loop_bandwidth
from decodilo.scaling.capacity_plan import build_capacity_plan
from decodilo.scaling.checkpointing import estimate_checkpointing
from decodilo.scaling.model_size import (
    estimate_optimizer_state_bytes,
    estimate_parameter_bytes,
    human_readable_bytes,
)
from decodilo.sim.runner import SimulationConfig, run_simulation
from decodilo.storage.artifact_index import build_artifact_index
from decodilo.storage.artifact_reference_audit import audit_artifact_references
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.gc import plan_artifact_gc, run_artifact_gc
from decodilo.storage.lifecycle_policy import ArtifactRetentionPolicy
from decodilo.syncer.event_segments import EventSegmentReader
from decodilo.syncer.recovery_audit import validate_recovery_manifest_chain
from decodilo.syncer.replay_stress import compare_genesis_and_snapshot_replay


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _cmd_simulate(args: argparse.Namespace) -> int:
    config = SimulationConfig(
        learners=args.learners,
        vector_dim=args.vector_dim,
        num_fragments=args.fragments,
        steps=args.steps,
        local_steps_per_sync=args.local_steps_per_sync,
        min_quorum=args.min_quorum,
        grace_window_ticks=args.grace_window,
        max_staleness_versions=args.max_staleness,
        seed=args.seed,
        outer_lr=args.outer_lr,
    )
    result = run_simulation(config, event_log_path=args.event_log)
    if args.report_json is not None:
        result.write_report_json(args.report_json)
    _print_json(result.to_dict())
    return 0


def _cmd_prices_lambda(args: argparse.Namespace) -> int:
    prices = parse_lambda_pricing_html(args.from_fixture, source_url=str(args.from_fixture))
    _print_json({"prices": [price.model_dump(mode="json") for price in prices]})
    return 0


def _cmd_budget_estimate(args: argparse.Namespace) -> int:
    snapshot = None
    snapshot_record = None
    if args.price_snapshot is not None:
        snapshot = load_price_snapshot(args.price_snapshot)
        require_usable_snapshot(
            snapshot,
            allow_sample_prices=args.allow_sample_prices,
            allow_stale_prices=args.allow_stale_prices,
            max_price_age_days=args.max_price_age_days,
        )
        snapshot_record = query_snapshot_price(
            snapshot,
            gpu_type=args.gpu_type,
            gpus_per_instance=args.gpus_per_instance,
            instance_type=args.instance_type,
            allow_ambiguous_price=args.allow_ambiguous_price,
        )
        price = snapshot_record.to_price_profile()
    else:
        prices = load_lambda_prices_from_json(args.price_json) if args.price_json else None
        price = get_price(
            prices,
            provider="lambda",
            gpu_type=args.gpu_type,
            gpus_per_instance=args.gpus_per_instance,
            instance_type=args.instance_type,
            allow_ambiguous_price=args.allow_ambiguous_price,
        )
    hourly_cost = hourly_cost_for_cluster(args.instances, price)
    estimated_cost = hourly_cost * args.hours
    max_run_budget = args.max_run_budget if args.max_run_budget is not None else args.credits
    guard = BudgetGuard(
        starting_credits=args.credits,
        estimated_committed_spend=args.committed_spend,
        actual_observed_spend=args.observed_spend,
        safety_buffer_pct=args.safety_buffer_pct,
    )
    decision = guard.check_run(
        estimated_run_cost=estimated_cost,
        max_run_budget=max_run_budget,
    )
    total_gpus = args.instances * price.gpus_per_instance
    manifest = None
    if snapshot is not None and snapshot_record is not None:
        manifest = build_run_budget_manifest(
            run_id=args.run_id or "budget-estimate",
            provider=snapshot.provider,
            mode=args.mode,
            price_snapshot_id=snapshot.snapshot_id,
            selected_price_record_ids=[snapshot_record.record_id],
            planned_instances=args.instances,
            gpus_per_instance=snapshot_record.gpus_per_instance,
            planned_hours=args.hours,
            base_estimated_cost=estimated_cost,
            safety_buffer_percentage=args.safety_buffer_pct,
            safety_buffer_adjusted_cost=decision.safety_buffer_adjusted_cost,
            max_run_budget=max_run_budget,
            starting_credits=args.credits,
            projected_remaining_credits=decision.projected_remaining_credits,
            allow_sample_prices=args.allow_sample_prices,
            allow_stale_prices=args.allow_stale_prices,
        )
    _print_json(
        {
            "selected_provider": price.provider,
            "selected_gpu_type": price.gpu_type,
            "selected_instance_shape": price.instance_type,
            "price_per_gpu_hour": price.price_per_gpu_hour,
            "price_per_instance_hour": price.price_per_instance_hour,
            "price_basis": "instance-hour",
            "instances": args.instances,
            "total_gpus": total_gpus,
            "planned_hours": args.hours,
            "base_estimated_cost": estimated_cost,
            "safety_buffer_pct": args.safety_buffer_pct,
            "safety_buffer_adjusted_cost": decision.safety_buffer_adjusted_cost,
            "projected_remaining_credits": decision.projected_remaining_credits,
            "price_source_url": price.source_url,
            "price_source_timestamp": price.source_timestamp,
            "snapshot_id": snapshot.snapshot_id if snapshot is not None else None,
            "record_id": snapshot_record.record_id if snapshot_record is not None else None,
            "tax_included": price.tax_included,
            "price": price.model_dump(mode="json"),
            "hours": args.hours,
            "hourly_cost": hourly_cost,
            "estimated_cost": estimated_cost,
            "budget_decision": decision.model_dump(mode="json"),
            "budget_manifest": manifest.model_dump(mode="json") if manifest else None,
        }
    )
    return 0


def _cmd_prices_snapshot_import_json(args: argparse.Namespace) -> int:
    snapshot = import_json_snapshot(
        provider=args.provider,
        input_path=args.input,
        output_path=args.out,
        source_type=PriceSourceType.FIXTURE if args.sample else PriceSourceType.MANUAL_JSON,
        is_sample_data=args.sample,
    )
    _print_json(snapshot.model_dump(mode="json"))
    return 0


def _cmd_prices_snapshot_import_html(args: argparse.Namespace) -> int:
    snapshot = import_html_snapshot(
        provider=args.provider,
        input_path=args.input,
        output_path=args.out,
        source_type=PriceSourceType.FIXTURE if args.sample else PriceSourceType.MANUAL_HTML,
        is_sample_data=args.sample,
    )
    _print_json(snapshot.model_dump(mode="json"))
    return 0


def _cmd_local_run(args: argparse.Namespace) -> int:
    return local_runner.main(args)


def _cmd_local_validate_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report_json).read_text(encoding="utf-8"))
    result = validate_report_payload(report)
    _print_json(result.model_dump(mode="json"))
    return 0 if result.passed else 1


def _cmd_local_artifacts(args: argparse.Namespace) -> int:
    workdir = Path(args.workdir)
    report_path = workdir / "report.json"
    existing_path = workdir / "artifacts.json"
    if existing_path.exists():
        manifest = ArtifactManifest.model_validate_json(existing_path.read_text(encoding="utf-8"))
    else:
        manifest = build_artifact_manifest(
            run_id="unknown",
            workdir=workdir,
            run_spec_path=workdir / "run_spec.json",
            report_path=report_path,
            event_log_path=workdir / "events.jsonl",
            syncer_checkpoint_paths=sorted(workdir.glob("syncer_checkpoint.json")),
            learner_checkpoint_paths=sorted(workdir.glob("learner-*.checkpoint.json")),
            learner_log_paths=sorted(workdir.glob("learner-*.log")),
            price_snapshot_paths=[],
        )
        write_artifact_manifest(existing_path, manifest)
    errors = validate_artifact_manifest(manifest)
    _print_json({"manifest": manifest.model_dump(mode="json"), "errors": errors})
    return 0 if not errors else 1


def _cmd_local_fault_matrix(args: argparse.Namespace) -> int:
    cases = [case.strip() for case in args.cases.split(",") if case.strip()]
    base = LocalRunConfig(
        learners=args.learners,
        steps=args.steps,
        min_quorum=args.min_quorum,
        seed=args.seed,
        workdir=args.workdir,
        report_json=args.workdir / "report.json",
        vector_dim=args.vector_dim,
        fragments=args.fragments,
        local_steps_per_sync=args.local_steps_per_sync,
        heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        heartbeat_timeout_seconds=args.heartbeat_timeout_seconds,
        update_long_poll_timeout_seconds=args.update_long_poll_timeout_seconds,
        step_delay_seconds=args.step_delay_seconds,
        run_id=args.run_id or "fault-matrix",
    )
    summary = run_fault_matrix(base_config=base, cases=cases)
    _print_json(summary)
    return 0 if all(item["passed"] for item in summary["cases"].values()) else 1


def _cmd_local_soak(args: argparse.Namespace) -> int:
    profile = get_soak_profile(args.profile)
    trainer = args.trainer or profile.trainer
    trainer_config = json.loads(args.trainer_config_json or "{}")
    chunked_profile = profile.name in {"chunked_ci", "binary_chunked_ci"}
    binary_profile = profile.name == "binary_chunked_ci"
    cases = (
        [case.strip() for case in args.cases.split(",") if case.strip()]
        if args.cases
        else list(profile.cases)
    )
    steps = args.steps if args.steps is not None else profile.steps
    if args.long:
        steps *= 3
    vector_dim = args.vector_dim if args.vector_dim is not None else profile.vector_dim
    vector_dim = local_runner._effective_vector_dim(
        trainer_type=trainer,
        trainer_config=trainer_config,
        requested_vector_dim=vector_dim,
    )
    base = LocalRunConfig(
        learners=args.learners if args.learners is not None else profile.learners,
        steps=steps,
        min_quorum=args.min_quorum if args.min_quorum is not None else profile.min_quorum,
        seed=args.seed,
        workdir=args.workdir,
        report_json=args.workdir / "report.json",
        vector_dim=vector_dim,
        fragments=args.fragments if args.fragments is not None else profile.fragments,
        local_steps_per_sync=(
            args.local_steps_per_sync
            if args.local_steps_per_sync is not None
            else profile.local_steps_per_sync
        ),
        trainer_type=trainer,
        trainer_config=trainer_config,
        heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        heartbeat_timeout_seconds=args.heartbeat_timeout_seconds,
        update_long_poll_timeout_seconds=args.update_long_poll_timeout_seconds,
        step_delay_seconds=args.step_delay_seconds,
        max_total_inflight_bytes=args.max_total_inflight_bytes,
        run_id=args.run_id or "soak",
        payload_storage_mode="chunked" if chunked_profile else "inline",
        checkpoint_storage_mode="chunked" if chunked_profile else "inline",
        merge_mode="streaming_chunked" if chunked_profile else "in_memory",
        global_update_storage_mode="chunked" if chunked_profile else "inline",
        chunk_size_bytes=1024 * 1024,
        memory_budget_mb=1 if chunked_profile else None,
        allow_spill_to_disk=chunked_profile,
        syncer_checkpoint_interval_rounds=1 if chunked_profile else 0,
        tensor_artifact_codec="binary_v1" if binary_profile else "json_safe",
        fragment_artifact_codec="binary_v1" if binary_profile else "json_safe",
        checkpoint_artifact_codec="binary_v1" if binary_profile else "json_safe",
    )
    summary = run_local_soak(
        base_config=base,
        cases=cases,
        long=False,
        profile=profile.name,
        trainer=trainer,
    )
    _print_json(summary)
    return 0 if summary["cases_failed"] == 0 else 1


def _cmd_perf_local_overhead(args: argparse.Namespace) -> int:
    config = LocalRunConfig(
        learners=args.learners,
        steps=args.steps,
        min_quorum=args.min_quorum,
        seed=args.seed,
        workdir=args.workdir,
        report_json=args.workdir / "report.json",
        vector_dim=args.vector_dim,
        fragments=args.fragments,
        local_steps_per_sync=args.local_steps_per_sync,
        trainer_type=args.trainer,
        heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        heartbeat_timeout_seconds=args.heartbeat_timeout_seconds,
        update_long_poll_timeout_seconds=args.update_long_poll_timeout_seconds,
        step_delay_seconds=args.step_delay_seconds,
        payload_storage_mode=args.payload_storage_mode,
        global_update_storage_mode=args.global_update_storage_mode,
        checkpoint_storage_mode=args.checkpoint_storage_mode,
        merge_mode=args.merge_mode,
        tensor_artifact_codec=args.tensor_artifact_codec,
        fragment_artifact_codec=args.fragment_artifact_codec,
        checkpoint_artifact_codec=args.checkpoint_artifact_codec,
        chunk_size_bytes=args.chunk_size_mb * 1024 * 1024,
        memory_budget_mb=args.memory_budget_mb,
        allow_spill_to_disk=args.allow_spill_to_disk,
        run_id=args.run_id or "perf-local-overhead",
    )
    report = run_local_overhead_harness(config=config, out=args.out)
    _print_json(
        {
            "run_id": report.run_id,
            "out": str(args.out),
            "replay_passed": report.validation["replay_passed"],
            "metric_validation_passed": report.validation["metric_validation_passed"],
            "useful_tokens_per_second": report.derived_ratios["useful_tokens_per_second"],
        }
    )
    return 0 if all(report.validation.values()) else 1


def _cmd_perf_merge_benchmark(args: argparse.Namespace) -> int:
    report = run_merge_benchmark(
        workdir=args.workdir,
        elements=args.elements,
        learners=args.learners,
        chunk_size_kb=args.chunk_size_kb,
        dtype=args.dtype,
        outer_lr=args.outer_lr,
        out=args.out,
    )
    _print_json(
        {
            "out": str(args.out),
            "validation_passed": report["validation_passed"],
            "bytes_read": report["bytes_read"],
            "bytes_written": report["bytes_written"],
        }
    )
    return 0 if report["validation_passed"] else 1


def _cmd_perf_artifact_io(args: argparse.Namespace) -> int:
    report = run_artifact_io_baseline(
        workdir=args.workdir,
        total_mb=args.total_mb,
        chunk_size_kb=args.chunk_size_kb,
        out=args.out,
    )
    _print_json(
        {
            "out": str(args.out),
            "validation_passed": report["validation_passed"],
            "bytes_read": report["bytes_read"],
            "bytes_written": report["bytes_written"],
        }
    )
    return 0 if report["validation_passed"] else 1


def _cmd_perf_compare_codecs(args: argparse.Namespace) -> int:
    report = run_compare_codecs(
        workdir=args.workdir,
        elements=args.elements,
        out=args.out,
    )
    _print_json(
        {
            "out": str(args.out),
            "validation_passed": report["validation_passed"],
            "json_safe_bytes": report["json_safe_bytes"],
            "binary_v1_bytes": report["binary_v1_bytes"],
        }
    )
    return 0 if report["validation_passed"] else 1


def _cmd_cloud_dry_run_lambda(args: argparse.Namespace) -> int:
    planner = LambdaDryRunPlanner()
    report = planner.build_plan(
        run_id=args.run_id,
        price_snapshot_path=args.price_snapshot,
        gpu_type=args.gpu_type,
        gpus_per_instance=args.gpus_per_instance,
        nodes=args.nodes,
        hours=args.hours,
        credits=args.credits,
        max_run_budget=args.max_run_budget,
        region=args.region,
        run_spec_path=args.run_spec,
        allow_sample_prices=args.allow_sample_prices,
        allow_stale_prices=args.allow_stale_prices,
        max_price_age_days=args.max_price_age_days,
        safety_buffer_percentage=args.safety_buffer_percentage,
        instance_type=args.instance_type,
        params=args.params,
        bytes_per_param=args.bytes_per_param,
        expected_tokens_per_second=args.expected_tokens_per_second,
        expected_goodput=args.expected_goodput,
        sync_interval_steps=args.sync_interval_steps,
        local_step_seconds=args.local_step_seconds,
        compression_bits=args.compression_bits,
        num_learners=args.learners,
    )
    if args.out is not None:
        write_cloud_dry_run_report(args.out, report)
    _print_json(
        {
            "run_id": report.plan.run_id,
            "provider": report.plan.provider,
            "launch_allowed": report.plan.launch_allowed,
            "reason_launch_not_allowed": report.plan.reason_launch_not_allowed,
            "base_estimated_cost": report.plan.base_estimated_cost,
            "safety_buffer_adjusted_cost": report.plan.safety_buffer_adjusted_cost,
            "projected_remaining_credits": report.plan.projected_remaining_credits,
            "price_snapshot_id": report.plan.price_snapshot_id,
            "selected_price_record_id": report.plan.selected_price_record_id,
            "out": str(args.out) if args.out else None,
            "validation_errors": report.validation_errors,
        }
    )
    return 0 if not report.validation_errors and report.plan.launch_allowed is False else 1


def _cmd_cloud_dry_run_validate(args: argparse.Namespace) -> int:
    errors = validate_cloud_dry_run_report(args.plan_json)
    report = load_cloud_dry_run_report(args.plan_json)
    _print_json(
        {
            "launch_allowed": report.plan.launch_allowed,
            "validation_errors": errors,
            "passed": not errors and report.plan.launch_allowed is False,
        }
    )
    return 0 if not errors and report.plan.launch_allowed is False else 1


def _cmd_cloud_launch_review(args: argparse.Namespace) -> int:
    report = load_cloud_dry_run_report(args.dry_run_plan)
    checklist = build_launch_review_checklist(
        report,
        operator_acknowledged=args.operator_acknowledged,
    )
    write_launch_review_checklist(args.out, checklist)
    _print_json(
        {
            "run_id": checklist.run_id,
            "provider": checklist.provider,
            "passed": checklist.passed,
            "launch_allowed": checklist.launch_allowed,
            "out": str(args.out),
        }
    )
    return 0


def _cmd_cloud_launch_disabled_test(args: argparse.Namespace) -> int:
    report = load_cloud_dry_run_report(args.dry_run_plan)
    try:
        DisabledCloudLauncher().launch(LaunchRequest(plan=report.plan))
    except LaunchDisabledError as exc:
        _print_json({"launch_disabled": True, "error": str(exc)})
        return 0
    _print_json({"launch_disabled": False, "error": "disabled launcher unexpectedly launched"})
    return 1


def _chunk_store_root_for_manifest(manifest_path: Path) -> Path:
    if manifest_path.parent.name == "manifests":
        return manifest_path.parent.parent
    sibling_store = manifest_path.parent / "store"
    if sibling_store.exists():
        return sibling_store
    resolved = manifest_path.resolve()
    for parent in resolved.parents:
        if parent.name == "artifacts":
            artifact_store = parent / "store"
            if artifact_store.exists():
                return artifact_store
            workdir_chunks = parent.parent / "chunks"
            if workdir_chunks.exists():
                return workdir_chunks
    return manifest_path.parent


def _cmd_storage_inspect_artifact(args: argparse.Namespace) -> int:
    root = args.chunk_root or _chunk_store_root_for_manifest(args.manifest_json)
    store = ChunkStore(root)
    manifest = store.read_manifest(args.manifest_json)
    _print_json(
        {
            **manifest.model_dump(mode="json"),
            "chunk_count": len(manifest.chunk_hashes),
            "storage_root": str(root),
        }
    )
    return 0


def _cmd_storage_verify_artifact(args: argparse.Namespace) -> int:
    root = args.chunk_root or _chunk_store_root_for_manifest(args.manifest_json)
    store = ChunkStore(root)
    manifest = store.read_manifest(args.manifest_json)
    store.verify_manifest(manifest)
    _print_json(
        {
            "artifact_id": manifest.artifact_id,
            "verified": True,
            "total_bytes": manifest.total_bytes,
            "chunk_count": len(manifest.chunk_hashes),
            "root_hash": manifest.root_hash,
            "manifest_hash": manifest.manifest_hash,
            "storage_root": str(root),
        }
    )
    return 0


def _cmd_artifacts_index(args: argparse.Namespace) -> int:
    index = build_artifact_index(args.workdir)
    if args.out is not None:
        args.out.write_text(
            json.dumps(index.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    _print_json(index.model_dump(mode="json"))
    return 0


def _cmd_artifacts_gc_plan(args: argparse.Namespace) -> int:
    plan = plan_artifact_gc(
        workdir=args.workdir,
        policy=ArtifactRetentionPolicy(dry_run=True, allow_incomplete=args.allow_incomplete),
    )
    if args.out is not None:
        args.out.write_text(
            json.dumps(plan.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    _print_json(plan.model_dump(mode="json"))
    return 0 if not plan.errors else 1


def _cmd_artifacts_gc(args: argparse.Namespace) -> int:
    report = run_artifact_gc(
        workdir=args.workdir,
        apply=args.apply,
        policy=ArtifactRetentionPolicy(
            dry_run=not args.apply,
            allow_incomplete=args.allow_incomplete,
        ),
    )
    if args.out is not None:
        args.out.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    _print_json(report.model_dump(mode="json"))
    return 0 if not report.errors else 1


def _cmd_artifacts_audit(args: argparse.Namespace) -> int:
    report = audit_artifact_references(args.workdir)
    if args.out is not None:
        args.out.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    _print_json(report.model_dump(mode="json"))
    return 0 if report.passed else 1


def _cmd_run_inspect(args: argparse.Namespace) -> int:
    _print_json(inspect_run(args.workdir).model_dump(mode="json"))
    return 0


def _cmd_run_validate(args: argparse.Namespace) -> int:
    result = validate_run(args.workdir)
    _print_json(result.model_dump(mode="json"))
    return 0 if result.passed else 1


def _cmd_run_compact(args: argparse.Namespace) -> int:
    result = compact_run(args.workdir, out=args.out)
    _print_json(result.model_dump(mode="json"))
    return 0 if not result.errors else 1


def _cmd_recovery_validate_chain(args: argparse.Namespace) -> int:
    report = validate_recovery_manifest_chain(args.workdir)
    _print_json(report.model_dump(mode="json"))
    return 0 if report.passed else 1


def _cmd_events_validate_segments(args: argparse.Namespace) -> int:
    manifest_path = args.workdir / "event_segments" / "segments_manifest.json"
    reader = EventSegmentReader(manifest_path)
    reader.validate()
    _print_json(
        {
            "passed": True,
            "segment_count": len(reader.manifest.segments),
            "manifest_path": str(manifest_path),
        }
    )
    return 0


def _cmd_replay_compare(args: argparse.Namespace) -> int:
    report = compare_genesis_and_snapshot_replay(args.workdir)
    _print_json(report.model_dump(mode="json"))
    return 0 if report.passed else 1


def _cmd_lifecycle_stress(args: argparse.Namespace) -> int:
    config = LocalRunConfig(
        learners=args.learners,
        steps=args.steps,
        min_quorum=args.min_quorum,
        seed=args.seed,
        workdir=args.workdir,
        report_json=args.workdir / "report.json",
        vector_dim=args.vector_dim,
        fragments=args.fragments,
        local_steps_per_sync=args.local_steps_per_sync,
        payload_storage_mode=args.payload_storage_mode,
        global_update_storage_mode=args.global_update_storage_mode,
        checkpoint_storage_mode=args.checkpoint_storage_mode,
        merge_mode=args.merge_mode,
        tensor_artifact_codec=args.tensor_artifact_codec,
        fragment_artifact_codec=args.fragment_artifact_codec,
        checkpoint_artifact_codec=args.checkpoint_artifact_codec,
        chunk_size_bytes=args.chunk_size_mb * 1024 * 1024,
        memory_budget_mb=args.memory_budget_mb,
        allow_spill_to_disk=args.allow_spill_to_disk,
        syncer_checkpoint_interval_rounds=max(1, args.compact_every_rounds),
        run_id=args.run_id,
    )
    report = run_lifecycle_stress(
        config=config,
        compact_every_rounds=args.compact_every_rounds,
        snapshot_every_compactions=args.snapshot_every_compactions,
        gc_plan_every_compactions=args.gc_plan_every_compactions,
        restart_syncer_every_compactions=args.restart_syncer_every_compactions,
        cycles=args.cycles,
        out=args.out,
    )
    _print_json(report.model_dump(mode="json"))
    return 0 if not report.errors else 1


def _cmd_dev_test_profile_summary(args: argparse.Namespace) -> int:
    _print_json(
        {
            "markers": [
                "unit",
                "integration",
                "slow",
                "soak",
                "perf",
                "torch_optional",
                "cloud_disabled",
                "storage",
                "replay",
                "runtime",
                "lifecycle",
            ],
            "recommended_commands": {
                "full": "pytest -q",
                "quick": (
                    "pytest -q -m "
                    '"not slow and not soak and not perf and not integration and not lifecycle"'
                ),
                "runtime_integration": 'pytest -q -m "runtime and integration"',
                "storage_replay": 'pytest -q -m "storage or replay"',
                "lifecycle": 'pytest -q -m "lifecycle"',
                "perf": 'pytest -q -m "perf"',
                "soak": 'pytest -q -m "soak"',
            },
            "note": "This summary is static and does not replace pytest collection.",
        }
    )
    return 0


def _cmd_preflight_local(args: argparse.Namespace) -> int:
    result = run_local_preflight(workdir=args.workdir)
    if args.out is not None:
        write_preflight_result(args.out, result)
        refresh_lifecycle_artifact_manifest(args.workdir)
    _print_json(result.model_dump(mode="json"))
    return 0 if result.passed else 1


def _cmd_preflight_cloud(args: argparse.Namespace) -> int:
    result = run_cloud_preflight(
        dry_run_plan=args.dry_run_plan,
        workdir=args.workdir,
        launch_review_path=args.launch_review,
    )
    if args.out is not None:
        write_preflight_result(args.out, result)
    _print_json(result.model_dump(mode="json"))
    return 0 if result.passed and result.launch_allowed is False else 1


def _cmd_trainer_list(args: argparse.Namespace) -> int:
    _print_json({"trainers": list_trainers(include_optional=True)})
    return 0


def _cmd_trainer_check(args: argparse.Namespace) -> int:
    result = run_trainer_check(trainer=args.trainer, workdir=args.workdir)
    _print_json(result)
    return 0 if not result.get("checks_failed") else 1


def _cmd_trainer_matrix(args: argparse.Namespace) -> int:
    matrix = run_trainer_matrix(
        workdir=args.workdir,
        include_optional=args.include_optional,
    )
    _print_json(matrix.model_dump(mode="json"))
    return 0 if matrix.passed else 1


def _cmd_syncer_serve(args: argparse.Namespace) -> int:
    return syncer_service.main(args)


def _cmd_learner_run(args: argparse.Namespace) -> int:
    return learner_worker.main(args)


def _cmd_scaling_bandwidth(args: argparse.Namespace) -> int:
    estimate = estimate_outer_loop_bandwidth(
        parameter_count=args.params,
        bytes_per_parameter=args.bytes_per_param,
        num_learners=args.learners,
        num_fragments=args.fragments,
        sync_interval_steps=args.sync_interval_steps,
        local_step_seconds=args.local_step_seconds,
        compression_bits=args.compression_bits,
    )
    _print_json(estimate.to_dict())
    return 0


def _cmd_scaling_capacity_plan(args: argparse.Namespace) -> int:
    snapshot = load_price_snapshot(args.price_snapshot)
    require_usable_snapshot(
        snapshot,
        allow_sample_prices=args.allow_sample_prices,
        allow_stale_prices=args.allow_stale_prices,
    )
    record = query_snapshot_price(
        snapshot,
        gpu_type=args.gpu_type,
        gpus_per_instance=args.gpus_per_instance,
        allow_ambiguous_price=args.allow_ambiguous_price,
    )
    plan = build_capacity_plan(
        price_record=record,
        num_instances=args.instances,
        planned_hours=args.hours,
        parameter_count=args.params,
        bytes_per_parameter=args.bytes_per_param,
        num_learners=args.learners,
        expected_tokens_per_second=args.expected_tokens_per_second,
        expected_goodput=args.expected_goodput,
        credit_budget=args.credits,
    )
    _print_json(plan.to_dict())
    return 0


def _cmd_scaling_large_state(args: argparse.Namespace) -> int:
    parameter_bytes = estimate_parameter_bytes(args.params, args.bytes_per_param)
    optimizer_bytes = estimate_optimizer_state_bytes(
        args.params,
        args.bytes_per_param,
        args.optimizer_multiplier,
    )
    total_state_bytes = parameter_bytes + optimizer_bytes
    chunk_size = int(args.chunk_size_mb * 1024 * 1024)
    memory_budget = int(args.memory_budget_mb * 1024 * 1024)
    estimated_chunk_count = int((total_state_bytes + chunk_size - 1) // chunk_size)
    fits_in_memory = total_state_bytes <= memory_budget
    checkpoint = estimate_checkpointing(
        parameter_count=args.params,
        bytes_per_parameter=args.bytes_per_param,
        optimizer_multiplier=args.optimizer_multiplier,
        num_learners=args.learners,
        checkpoint_interval_minutes=10,
        retention_count=2,
    )
    warnings = []
    if chunk_size > memory_budget:
        warnings.append("chunk size exceeds memory budget")
    if total_state_bytes > memory_budget:
        warnings.append("full model state exceeds memory budget; chunking is required")
    _print_json(
        {
            "parameter_count": args.params,
            "parameter_bytes": parameter_bytes,
            "optimizer_multiplier": args.optimizer_multiplier,
            "optimizer_state_bytes": optimizer_bytes,
            "total_state_bytes": total_state_bytes,
            "total_state_human": human_readable_bytes(total_state_bytes),
            "chunk_size_bytes": chunk_size,
            "estimated_chunk_count": estimated_chunk_count,
            "memory_budget_bytes": memory_budget,
            "fits_in_memory": fits_in_memory,
            "spill_required": not fits_in_memory,
            "learners": args.learners,
            "checkpointing": checkpoint.to_dict(),
            "warnings": warnings,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="decodilo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate = subparsers.add_parser("simulate", help="Run the CPU-only simulator")
    simulate.add_argument("--learners", type=int, default=4)
    simulate.add_argument("--steps", type=int, default=200)
    simulate.add_argument("--min-quorum", type=int, default=2)
    simulate.add_argument("--seed", type=int, default=123)
    simulate.add_argument("--vector-dim", type=int, default=8)
    simulate.add_argument("--fragments", type=int, default=2)
    simulate.add_argument("--local-steps-per-sync", type=int, default=10)
    simulate.add_argument("--grace-window", type=int, default=0)
    simulate.add_argument("--max-staleness", type=int, default=1)
    simulate.add_argument("--outer-lr", type=float, default=1.0)
    simulate.add_argument("--event-log", type=Path, default=None)
    simulate.add_argument("--report-json", type=Path, default=None)
    simulate.set_defaults(func=_cmd_simulate)

    prices = subparsers.add_parser("prices", help="Pricing sources")
    prices_sub = prices.add_subparsers(dest="provider", required=True)
    lambda_prices = prices_sub.add_parser("lambda", help="Parse Lambda pricing")
    lambda_prices.add_argument("--from-fixture", type=Path, required=True)
    lambda_prices.set_defaults(func=_cmd_prices_lambda)

    snapshot = prices_sub.add_parser("snapshot", help="Import price snapshots")
    snapshot_sub = snapshot.add_subparsers(dest="snapshot_command", required=True)
    import_json = snapshot_sub.add_parser("import-json")
    import_json.add_argument("--provider", required=True)
    import_json.add_argument("--input", type=Path, required=True)
    import_json.add_argument("--out", type=Path, required=True)
    import_json.add_argument("--sample", action="store_true")
    import_json.set_defaults(func=_cmd_prices_snapshot_import_json)
    import_html = snapshot_sub.add_parser("import-html")
    import_html.add_argument("--provider", required=True)
    import_html.add_argument("--input", type=Path, required=True)
    import_html.add_argument("--out", type=Path, required=True)
    import_html.add_argument("--sample", action="store_true")
    import_html.set_defaults(func=_cmd_prices_snapshot_import_html)

    budget = subparsers.add_parser("budget", help="Budget utilities")
    budget_sub = budget.add_subparsers(dest="budget_command", required=True)
    estimate = budget_sub.add_parser("estimate", help="Estimate run cost")
    estimate.add_argument("--credits", type=float, required=True)
    estimate.add_argument("--gpu-type", required=True)
    estimate.add_argument("--gpus-per-instance", type=int, required=True)
    estimate.add_argument("--instances", type=int, required=True)
    estimate.add_argument("--hours", type=float, required=True)
    estimate.add_argument("--instance-type", default=None)
    estimate.add_argument("--price-json", type=Path, default=None)
    estimate.add_argument("--price-snapshot", type=Path, default=None)
    estimate.add_argument("--max-run-budget", type=float, default=None)
    estimate.add_argument("--committed-spend", type=float, default=0.0)
    estimate.add_argument("--observed-spend", type=float, default=0.0)
    estimate.add_argument("--safety-buffer-pct", type=float, default=0.15)
    estimate.add_argument("--allow-ambiguous-price", action="store_true")
    estimate.add_argument("--allow-sample-prices", action="store_true")
    estimate.add_argument("--allow-stale-prices", action="store_true")
    estimate.add_argument("--max-price-age-days", type=int, default=7)
    estimate.add_argument("--mode", default="cloud-dry-run")
    estimate.add_argument("--run-id", default=None)
    estimate.set_defaults(func=_cmd_budget_estimate)

    local = subparsers.add_parser("local", help="Local multiprocessing runtime")
    local_sub = local.add_subparsers(dest="local_command", required=True)
    local_run = local_sub.add_parser("run", help="Run syncer and learners locally")
    local_run.add_argument("--learners", type=int, default=4)
    local_run.add_argument("--steps", type=int, default=200)
    local_run.add_argument("--min-quorum", type=int, default=2)
    local_run.add_argument("--seed", type=int, default=123)
    local_run.add_argument("--workdir", type=Path, default=None)
    local_run.add_argument("--report-json", type=Path, default=None)
    local_run.add_argument("--run-spec", type=Path, default=None)
    local_run.add_argument("--vector-dim", type=int, default=8)
    local_run.add_argument("--fragments", type=int, default=2)
    local_run.add_argument("--local-steps-per-sync", type=int, default=10)
    local_run.add_argument("--grace-window", type=int, default=0)
    local_run.add_argument("--max-staleness", type=int, default=1)
    local_run.add_argument("--learner-lr", type=float, default=0.05)
    local_run.add_argument("--outer-lr", type=float, default=1.0)
    local_run.add_argument("--trainer-type", default="numpy_convex")
    local_run.add_argument("--trainer", default=None)
    local_run.add_argument("--trainer-config-json", default="{}")
    local_run.add_argument("--heartbeat-interval-seconds", type=float, default=0.05)
    local_run.add_argument("--heartbeat-timeout-seconds", type=float, default=0.2)
    local_run.add_argument("--update-long-poll-timeout-seconds", type=float, default=0.005)
    local_run.add_argument("--step-delay-seconds", type=float, default=0.005)
    local_run.add_argument("--max-pending-messages-per-learner", type=int, default=128)
    local_run.add_argument("--max-pending-fragments-per-learner", type=int, default=1)
    local_run.add_argument("--max-inflight-bytes-per-learner", type=int, default=2_000_000)
    local_run.add_argument("--max-total-inflight-bytes", type=int, default=10_000_000)
    local_run.add_argument("--memory-budget-mb", type=int, default=None)
    local_run.add_argument("--allow-spill-to-disk", action="store_true")
    local_run.add_argument("--spill-dir", type=Path, default=None)
    local_run.add_argument("--max-spill-mb", type=int, default=None)
    local_run.add_argument("--chunked-checkpoints", action="store_true")
    local_run.add_argument(
        "--payload-storage-mode",
        choices=["inline", "chunked", "auto"],
        default="inline",
    )
    local_run.add_argument(
        "--checkpoint-storage-mode",
        choices=["inline", "chunked", "dual"],
        default="inline",
    )
    local_run.add_argument(
        "--merge-mode",
        choices=["in_memory", "streaming_chunked", "auto"],
        default="in_memory",
    )
    local_run.add_argument(
        "--global-update-storage-mode",
        choices=["inline", "chunked", "auto"],
        default="inline",
    )
    local_run.add_argument("--artifact-root", type=Path, default=None)
    local_run.add_argument("--chunk-store-root", type=Path, default=None)
    local_run.add_argument("--inline-payload-max-bytes", type=int, default=1_000_000)
    local_run.add_argument("--chunk-size-mb", type=int, default=1)
    local_run.add_argument("--require-chunked-for-large-state", action="store_true")
    local_run.add_argument(
        "--tensor-artifact-codec",
        choices=["json_safe", "binary_v1", "auto"],
        default="json_safe",
    )
    local_run.add_argument(
        "--fragment-artifact-codec",
        choices=["json_safe", "binary_v1", "auto"],
        default="json_safe",
    )
    local_run.add_argument(
        "--checkpoint-artifact-codec",
        choices=["json_safe", "binary_v1", "auto"],
        default="json_safe",
    )
    local_run.add_argument("--syncer-checkpoint-interval-rounds", type=int, default=0)
    local_run.add_argument("--restart-syncer-after-round", type=int, default=None)
    local_run.add_argument("--syncer-restart-timeout-seconds", type=float, default=3.0)
    local_run.add_argument("--price-snapshot", type=Path, default=None)
    local_run.add_argument("--allow-sample-prices", action="store_true")
    local_run.add_argument("--allow-stale-prices", action="store_true")
    local_run.add_argument("--credits", type=float, default=None)
    local_run.add_argument("--gpu-type", default=None)
    local_run.add_argument("--gpus-per-instance", type=int, default=None)
    local_run.add_argument("--instances", type=int, default=1)
    local_run.add_argument("--hours", type=float, default=None)
    local_run.add_argument("--max-run-budget", type=float, default=None)
    local_run.add_argument("--safety-buffer-pct", type=float, default=0.15)
    local_run.add_argument("--run-id", default=None)
    local_run.add_argument("--kill-learner", default=None)
    local_run.add_argument("--restart-learner", default=None)
    local_run.add_argument(
        "--slow-learner",
        default=None,
        help="Format: learner-id:factor=X:after-round=N",
    )
    local_run.add_argument(
        "--restore-learner",
        default=None,
        help="Format: learner-id:after-round=N",
    )
    local_run.set_defaults(func=_cmd_local_run)

    validate_report = local_sub.add_parser("validate-report", help="Validate local report metrics")
    validate_report.add_argument("report_json", type=Path)
    validate_report.set_defaults(func=_cmd_local_validate_report)

    artifacts = local_sub.add_parser("artifacts", help="Build or validate artifact manifest")
    artifacts.add_argument("workdir", type=Path)
    artifacts.set_defaults(func=_cmd_local_artifacts)

    fault_matrix = local_sub.add_parser("fault-matrix", help="Run deterministic local fault cases")
    fault_matrix.add_argument("--learners", type=int, default=4)
    fault_matrix.add_argument("--steps", type=int, default=120)
    fault_matrix.add_argument("--min-quorum", type=int, default=2)
    fault_matrix.add_argument("--seed", type=int, default=123)
    fault_matrix.add_argument("--workdir", type=Path, required=True)
    fault_matrix.add_argument(
        "--cases",
        default="learner_kill,learner_restart,slow_restore,syncer_restart",
    )
    fault_matrix.add_argument("--vector-dim", type=int, default=4)
    fault_matrix.add_argument("--fragments", type=int, default=3)
    fault_matrix.add_argument("--local-steps-per-sync", type=int, default=10)
    fault_matrix.add_argument("--heartbeat-interval-seconds", type=float, default=0.05)
    fault_matrix.add_argument("--heartbeat-timeout-seconds", type=float, default=0.2)
    fault_matrix.add_argument("--update-long-poll-timeout-seconds", type=float, default=0.005)
    fault_matrix.add_argument("--step-delay-seconds", type=float, default=0.003)
    fault_matrix.add_argument("--run-id", default=None)
    fault_matrix.set_defaults(func=_cmd_local_fault_matrix)

    soak = local_sub.add_parser("soak", help="Run short local soak cases")
    soak.add_argument("--profile", default="ci")
    soak.add_argument("--trainer", default=None)
    soak.add_argument("--trainer-config-json", default="{}")
    soak.add_argument("--learners", type=int, default=None)
    soak.add_argument("--steps", type=int, default=None)
    soak.add_argument("--min-quorum", type=int, default=None)
    soak.add_argument("--seed", type=int, default=123)
    soak.add_argument("--workdir", type=Path, required=True)
    soak.add_argument("--cases", default=None)
    soak.add_argument("--long", action="store_true")
    soak.add_argument("--vector-dim", type=int, default=None)
    soak.add_argument("--fragments", type=int, default=None)
    soak.add_argument("--local-steps-per-sync", type=int, default=None)
    soak.add_argument("--heartbeat-interval-seconds", type=float, default=0.05)
    soak.add_argument("--heartbeat-timeout-seconds", type=float, default=0.2)
    soak.add_argument("--update-long-poll-timeout-seconds", type=float, default=0.005)
    soak.add_argument("--step-delay-seconds", type=float, default=0.003)
    soak.add_argument("--max-total-inflight-bytes", type=int, default=10_000_000)
    soak.add_argument("--run-id", default=None)
    soak.set_defaults(func=_cmd_local_soak)

    perf = subparsers.add_parser("perf", help="Local performance harnesses")
    perf_sub = perf.add_subparsers(dest="perf_command", required=True)
    local_overhead = perf_sub.add_parser("local-overhead")
    local_overhead.add_argument("--workdir", type=Path, required=True)
    local_overhead.add_argument("--out", type=Path, required=True)
    local_overhead.add_argument("--trainer", default="numpy_convex")
    local_overhead.add_argument("--learners", type=int, default=2)
    local_overhead.add_argument("--steps", type=int, default=80)
    local_overhead.add_argument("--min-quorum", type=int, default=1)
    local_overhead.add_argument("--seed", type=int, default=123)
    local_overhead.add_argument("--vector-dim", type=int, default=8)
    local_overhead.add_argument("--fragments", type=int, default=1)
    local_overhead.add_argument("--local-steps-per-sync", type=int, default=10)
    local_overhead.add_argument("--heartbeat-interval-seconds", type=float, default=0.05)
    local_overhead.add_argument("--heartbeat-timeout-seconds", type=float, default=0.2)
    local_overhead.add_argument("--update-long-poll-timeout-seconds", type=float, default=0.005)
    local_overhead.add_argument("--step-delay-seconds", type=float, default=0.003)
    local_overhead.add_argument(
        "--payload-storage-mode",
        choices=["inline", "chunked", "auto"],
        default="chunked",
    )
    local_overhead.add_argument(
        "--global-update-storage-mode",
        choices=["inline", "chunked", "auto"],
        default="chunked",
    )
    local_overhead.add_argument(
        "--checkpoint-storage-mode",
        choices=["inline", "chunked", "dual"],
        default="chunked",
    )
    local_overhead.add_argument(
        "--merge-mode",
        choices=["in_memory", "streaming_chunked", "auto"],
        default="streaming_chunked",
    )
    local_overhead.add_argument(
        "--tensor-artifact-codec",
        choices=["json_safe", "binary_v1", "auto"],
        default="binary_v1",
    )
    local_overhead.add_argument(
        "--fragment-artifact-codec",
        choices=["json_safe", "binary_v1", "auto"],
        default="binary_v1",
    )
    local_overhead.add_argument(
        "--checkpoint-artifact-codec",
        choices=["json_safe", "binary_v1", "auto"],
        default="binary_v1",
    )
    local_overhead.add_argument("--chunk-size-mb", type=int, default=1)
    local_overhead.add_argument("--memory-budget-mb", type=int, default=16)
    local_overhead.add_argument("--allow-spill-to-disk", action="store_true")
    local_overhead.add_argument("--run-id", default=None)
    local_overhead.set_defaults(func=_cmd_perf_local_overhead)

    merge_benchmark = perf_sub.add_parser("merge-benchmark")
    merge_benchmark.add_argument("--workdir", type=Path, required=True)
    merge_benchmark.add_argument("--elements", type=int, required=True)
    merge_benchmark.add_argument("--learners", type=int, required=True)
    merge_benchmark.add_argument("--chunk-size-kb", type=int, required=True)
    merge_benchmark.add_argument("--dtype", choices=["float32", "float64"], required=True)
    merge_benchmark.add_argument("--outer-lr", type=float, required=True)
    merge_benchmark.add_argument("--out", type=Path, required=True)
    merge_benchmark.set_defaults(func=_cmd_perf_merge_benchmark)

    artifact_io = perf_sub.add_parser("artifact-io")
    artifact_io.add_argument("--workdir", type=Path, required=True)
    artifact_io.add_argument("--total-mb", type=int, required=True)
    artifact_io.add_argument("--chunk-size-kb", type=int, required=True)
    artifact_io.add_argument("--out", type=Path, required=True)
    artifact_io.set_defaults(func=_cmd_perf_artifact_io)

    compare_codecs = perf_sub.add_parser("compare-codecs")
    compare_codecs.add_argument("--workdir", type=Path, required=True)
    compare_codecs.add_argument("--elements", type=int, required=True)
    compare_codecs.add_argument("--out", type=Path, required=True)
    compare_codecs.set_defaults(func=_cmd_perf_compare_codecs)

    cloud = subparsers.add_parser("cloud", help="Cloud dry-run planning")
    cloud_sub = cloud.add_subparsers(dest="cloud_command", required=True)
    dry_run = cloud_sub.add_parser("dry-run", help="Create or validate cloud dry-run plans")
    dry_run_sub = dry_run.add_subparsers(dest="dry_run_command", required=True)
    cloud_lambda = dry_run_sub.add_parser("lambda", help="Build a Lambda dry-run plan")
    cloud_lambda.add_argument("--price-snapshot", type=Path, required=True)
    cloud_lambda.add_argument("--gpu-type", required=True)
    cloud_lambda.add_argument("--gpus-per-instance", type=int, required=True)
    cloud_lambda.add_argument("--nodes", type=int, required=True)
    cloud_lambda.add_argument("--hours", type=float, required=True)
    cloud_lambda.add_argument("--credits", type=float, required=True)
    cloud_lambda.add_argument("--max-run-budget", type=float, required=True)
    cloud_lambda.add_argument("--region", default=None)
    cloud_lambda.add_argument("--run-spec", type=Path, default=None)
    cloud_lambda.add_argument("--out", type=Path, default=None)
    cloud_lambda.add_argument("--run-id", default="cloud-dry-run")
    cloud_lambda.add_argument("--instance-type", default=None)
    cloud_lambda.add_argument("--allow-sample-prices", action="store_true")
    cloud_lambda.add_argument("--allow-stale-prices", action="store_true")
    cloud_lambda.add_argument("--max-price-age-days", type=int, default=7)
    cloud_lambda.add_argument("--safety-buffer-percentage", type=float, default=0.15)
    cloud_lambda.add_argument("--params", type=int, default=None)
    cloud_lambda.add_argument("--bytes-per-param", type=float, default=None)
    cloud_lambda.add_argument("--expected-tokens-per-second", type=float, default=None)
    cloud_lambda.add_argument("--expected-goodput", type=float, default=None)
    cloud_lambda.add_argument("--sync-interval-steps", type=int, default=500)
    cloud_lambda.add_argument("--local-step-seconds", type=float, default=1.0)
    cloud_lambda.add_argument("--compression-bits", type=int, default=None)
    cloud_lambda.add_argument("--learners", type=int, default=None)
    cloud_lambda.set_defaults(func=_cmd_cloud_dry_run_lambda)
    cloud_validate = dry_run_sub.add_parser("validate", help="Validate a cloud dry-run plan")
    cloud_validate.add_argument("plan_json", type=Path)
    cloud_validate.set_defaults(func=_cmd_cloud_dry_run_validate)
    launch_review = cloud_sub.add_parser("launch-review", help="Write a disabled launch checklist")
    launch_review.add_argument("--dry-run-plan", type=Path, required=True)
    launch_review.add_argument("--out", type=Path, required=True)
    launch_review.add_argument("--operator-acknowledged", action="store_true")
    launch_review.set_defaults(func=_cmd_cloud_launch_review)
    launch_disabled = cloud_sub.add_parser(
        "launch-disabled-test",
        help="Verify the disabled launcher refuses to launch",
    )
    launch_disabled.add_argument("--dry-run-plan", type=Path, required=True)
    launch_disabled.set_defaults(func=_cmd_cloud_launch_disabled_test)

    storage = subparsers.add_parser("storage", help="Chunked storage utilities")
    storage_sub = storage.add_subparsers(dest="storage_command", required=True)
    inspect_artifact = storage_sub.add_parser("inspect-artifact")
    inspect_artifact.add_argument("manifest_json", type=Path)
    inspect_artifact.add_argument("--chunk-root", type=Path, default=None)
    inspect_artifact.set_defaults(func=_cmd_storage_inspect_artifact)
    verify_artifact = storage_sub.add_parser("verify-artifact")
    verify_artifact.add_argument("manifest_json", type=Path)
    verify_artifact.add_argument("--chunk-root", type=Path, default=None)
    verify_artifact.set_defaults(func=_cmd_storage_verify_artifact)

    artifacts_top = subparsers.add_parser("artifacts", help="Run artifact lifecycle utilities")
    artifacts_sub = artifacts_top.add_subparsers(dest="artifacts_command", required=True)
    artifacts_index = artifacts_sub.add_parser("index")
    artifacts_index.add_argument("--workdir", type=Path, required=True)
    artifacts_index.add_argument("--out", type=Path, default=None)
    artifacts_index.set_defaults(func=_cmd_artifacts_index)
    artifacts_audit = artifacts_sub.add_parser("audit")
    artifacts_audit.add_argument("--workdir", type=Path, required=True)
    artifacts_audit.add_argument("--out", type=Path, default=None)
    artifacts_audit.set_defaults(func=_cmd_artifacts_audit)
    gc_plan = artifacts_sub.add_parser("gc-plan")
    gc_plan.add_argument("--workdir", type=Path, required=True)
    gc_plan.add_argument("--out", type=Path, default=None)
    gc_plan.add_argument("--allow-incomplete", action="store_true")
    gc_plan.set_defaults(func=_cmd_artifacts_gc_plan)
    gc = artifacts_sub.add_parser("gc")
    gc.add_argument("--workdir", type=Path, required=True)
    gc.add_argument("--apply", action="store_true")
    gc.add_argument("--out", type=Path, default=None)
    gc.add_argument("--allow-incomplete", action="store_true")
    gc.set_defaults(func=_cmd_artifacts_gc)

    run = subparsers.add_parser("run", help="Run lifecycle utilities")
    run_sub = run.add_subparsers(dest="run_command", required=True)
    run_inspect = run_sub.add_parser("inspect")
    run_inspect.add_argument("--workdir", type=Path, required=True)
    run_inspect.set_defaults(func=_cmd_run_inspect)
    run_validate = run_sub.add_parser("validate")
    run_validate.add_argument("--workdir", type=Path, required=True)
    run_validate.set_defaults(func=_cmd_run_validate)
    run_compact = run_sub.add_parser("compact")
    run_compact.add_argument("--workdir", type=Path, required=True)
    run_compact.add_argument("--out", type=Path, required=True)
    run_compact.set_defaults(func=_cmd_run_compact)

    lifecycle = subparsers.add_parser("lifecycle", help="Lifecycle stress utilities")
    lifecycle_sub = lifecycle.add_subparsers(dest="lifecycle_command", required=True)
    stress = lifecycle_sub.add_parser("stress")
    stress.add_argument("--workdir", type=Path, required=True)
    stress.add_argument("--out", type=Path, required=True)
    stress.add_argument("--learners", type=int, default=2)
    stress.add_argument("--steps", type=int, default=120)
    stress.add_argument("--min-quorum", type=int, default=1)
    stress.add_argument("--seed", type=int, default=123)
    stress.add_argument("--vector-dim", type=int, default=8)
    stress.add_argument("--fragments", type=int, default=2)
    stress.add_argument("--local-steps-per-sync", type=int, default=10)
    stress.add_argument("--payload-storage-mode", default="chunked")
    stress.add_argument("--global-update-storage-mode", default="chunked")
    stress.add_argument("--checkpoint-storage-mode", default="chunked")
    stress.add_argument("--merge-mode", default="streaming_chunked")
    stress.add_argument("--tensor-artifact-codec", default="binary_v1")
    stress.add_argument("--fragment-artifact-codec", default="binary_v1")
    stress.add_argument("--checkpoint-artifact-codec", default="binary_v1")
    stress.add_argument("--chunk-size-mb", type=int, default=1)
    stress.add_argument("--memory-budget-mb", type=int, default=16)
    stress.add_argument("--allow-spill-to-disk", action="store_true")
    stress.add_argument("--compact-every-rounds", type=int, default=3)
    stress.add_argument("--snapshot-every-compactions", type=int, default=2)
    stress.add_argument("--gc-plan-every-compactions", type=int, default=2)
    stress.add_argument("--restart-syncer-every-compactions", type=int, default=None)
    stress.add_argument("--cycles", type=int, default=2)
    stress.add_argument("--run-id", default=None)
    stress.set_defaults(func=_cmd_lifecycle_stress)

    recovery = subparsers.add_parser("recovery", help="Recovery manifest utilities")
    recovery_sub = recovery.add_subparsers(dest="recovery_command", required=True)
    validate_chain = recovery_sub.add_parser("validate-chain")
    validate_chain.add_argument("--workdir", type=Path, required=True)
    validate_chain.set_defaults(func=_cmd_recovery_validate_chain)

    events = subparsers.add_parser("events", help="Event segment utilities")
    events_sub = events.add_subparsers(dest="events_command", required=True)
    validate_segments = events_sub.add_parser("validate-segments")
    validate_segments.add_argument("--workdir", type=Path, required=True)
    validate_segments.set_defaults(func=_cmd_events_validate_segments)

    replay = subparsers.add_parser("replay", help="Replay utilities")
    replay_sub = replay.add_subparsers(dest="replay_command", required=True)
    compare = replay_sub.add_parser("compare")
    compare.add_argument("--workdir", type=Path, required=True)
    compare.add_argument("--genesis", action="store_true")
    compare.add_argument("--snapshot", default="latest")
    compare.set_defaults(func=_cmd_replay_compare)

    dev = subparsers.add_parser("dev", help="Developer utilities")
    dev_sub = dev.add_subparsers(dest="dev_command", required=True)
    test_profile = dev_sub.add_parser("test-profile-summary")
    test_profile.set_defaults(func=_cmd_dev_test_profile_summary)

    preflight = subparsers.add_parser("preflight", help="Local and cloud preflight gates")
    preflight_sub = preflight.add_subparsers(dest="preflight_command", required=True)
    preflight_local = preflight_sub.add_parser("local")
    preflight_local.add_argument("--workdir", type=Path, required=True)
    preflight_local.add_argument("--out", type=Path, default=None)
    preflight_local.set_defaults(func=_cmd_preflight_local)
    preflight_cloud = preflight_sub.add_parser("cloud")
    preflight_cloud.add_argument("--dry-run-plan", type=Path, required=True)
    preflight_cloud.add_argument("--workdir", type=Path, default=None)
    preflight_cloud.add_argument("--launch-review", type=Path, default=None)
    preflight_cloud.add_argument("--out", type=Path, default=None)
    preflight_cloud.set_defaults(func=_cmd_preflight_cloud)

    trainer = subparsers.add_parser("trainer", help="Trainer compatibility utilities")
    trainer_sub = trainer.add_subparsers(dest="trainer_command", required=True)
    trainer_list = trainer_sub.add_parser("list", help="List known trainers")
    trainer_list.set_defaults(func=_cmd_trainer_list)
    trainer_check = trainer_sub.add_parser("check", help="Run one trainer contract check")
    trainer_check.add_argument("--trainer", required=True)
    trainer_check.add_argument("--workdir", type=Path, required=True)
    trainer_check.set_defaults(func=_cmd_trainer_check)
    trainer_matrix = trainer_sub.add_parser("matrix", help="Run trainer compatibility matrix")
    trainer_matrix.add_argument("--workdir", type=Path, required=True)
    trainer_matrix.add_argument("--include-optional", action="store_true")
    trainer_matrix.set_defaults(func=_cmd_trainer_matrix)

    syncer = subparsers.add_parser("syncer", help=argparse.SUPPRESS)
    syncer_sub = syncer.add_subparsers(dest="syncer_command", required=True)
    serve = syncer_sub.add_parser("serve", help="Internal local syncer service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--ready-file", type=Path, required=True)
    serve.add_argument("--workdir", type=Path, required=True)
    serve.add_argument("--run-id", default=None)
    serve.add_argument("--learners", type=int, default=4)
    serve.add_argument("--steps", type=int, default=200)
    serve.add_argument("--vector-dim", type=int, default=8)
    serve.add_argument("--fragments", type=int, default=2)
    serve.add_argument("--local-steps-per-sync", type=int, default=10)
    serve.add_argument("--min-quorum", type=int, default=2)
    serve.add_argument("--grace-window", type=int, default=0)
    serve.add_argument("--max-staleness", type=int, default=1)
    serve.add_argument("--seed", type=int, default=123)
    serve.add_argument("--learner-lr", type=float, default=0.05)
    serve.add_argument("--outer-lr", type=float, default=1.0)
    serve.add_argument("--heartbeat-timeout-seconds", type=float, default=0.5)
    serve.add_argument("--heartbeat-check-interval-seconds", type=float, default=0.05)
    serve.add_argument("--update-long-poll-timeout-seconds", type=float, default=0.005)
    serve.add_argument("--max-learner-version-lag", type=int, default=2)
    serve.add_argument("--max-pending-messages-per-learner", type=int, default=128)
    serve.add_argument("--max-pending-fragments-per-learner", type=int, default=1)
    serve.add_argument("--max-inflight-bytes-per-learner", type=int, default=2_000_000)
    serve.add_argument("--max-total-inflight-bytes", type=int, default=10_000_000)
    serve.add_argument("--syncer-checkpoint-interval-rounds", type=int, default=0)
    serve.add_argument("--syncer-checkpoint-path", type=Path, default=None)
    serve.add_argument("--recover-from-checkpoint", action="store_true")
    serve.add_argument("--payload-storage-mode", default="inline")
    serve.add_argument("--checkpoint-storage-mode", default="inline")
    serve.add_argument("--merge-mode", default="in_memory")
    serve.add_argument("--global-update-storage-mode", default="inline")
    serve.add_argument("--artifact-root", type=Path, default=None)
    serve.add_argument("--chunk-store-root", type=Path, default=None)
    serve.add_argument("--inline-payload-max-bytes", type=int, default=1_000_000)
    serve.add_argument("--chunk-size-bytes", type=int, default=1024 * 1024)
    serve.add_argument("--tensor-artifact-codec", default="json_safe")
    serve.add_argument("--fragment-artifact-codec", default="json_safe")
    serve.add_argument("--checkpoint-artifact-codec", default="json_safe")
    serve.set_defaults(func=_cmd_syncer_serve)

    learner = subparsers.add_parser("learner", help=argparse.SUPPRESS)
    learner_sub = learner.add_subparsers(dest="learner_command", required=True)
    learner_run = learner_sub.add_parser("run", help="Internal local learner worker")
    learner_run.add_argument("--learner-id", required=True)
    learner_run.add_argument("--run-id", required=True)
    learner_run.add_argument("--host", default="127.0.0.1")
    learner_run.add_argument("--port", type=int, required=True)
    learner_run.add_argument("--workdir", type=Path, required=True)
    learner_run.add_argument("--steps", type=int, default=200)
    learner_run.add_argument("--local-steps-per-sync", type=int, default=10)
    learner_run.add_argument("--heartbeat-interval-seconds", type=float, default=0.05)
    learner_run.add_argument("--step-delay-seconds", type=float, default=0.005)
    learner_run.add_argument("--learner-lr", type=float, default=0.05)
    learner_run.add_argument("--slow-factor", type=float, default=1.0)
    learner_run.add_argument("--trainer-type", default="numpy_convex")
    learner_run.add_argument("--trainer-config-json", default="{}")
    learner_run.add_argument("--seed", type=int, default=123)
    learner_run.add_argument("--payload-storage-mode", default="inline")
    learner_run.add_argument("--global-update-storage-mode", default="inline")
    learner_run.add_argument("--artifact-root", type=Path, default=None)
    learner_run.add_argument("--chunk-store-root", type=Path, default=None)
    learner_run.add_argument("--inline-payload-max-bytes", type=int, default=1_000_000)
    learner_run.add_argument("--chunk-size-bytes", type=int, default=1024 * 1024)
    learner_run.add_argument("--tensor-artifact-codec", default="json_safe")
    learner_run.add_argument("--fragment-artifact-codec", default="json_safe")
    learner_run.add_argument("--checkpoint-artifact-codec", default="json_safe")
    learner_run.set_defaults(func=_cmd_learner_run)

    scaling = subparsers.add_parser("scaling", help="Scaling estimators")
    scaling_sub = scaling.add_subparsers(dest="scaling_command", required=True)
    bandwidth = scaling_sub.add_parser("bandwidth")
    bandwidth.add_argument("--params", type=int, required=True)
    bandwidth.add_argument("--bytes-per-param", type=float, required=True)
    bandwidth.add_argument("--learners", type=int, required=True)
    bandwidth.add_argument("--fragments", type=int, required=True)
    bandwidth.add_argument("--sync-interval-steps", type=int, required=True)
    bandwidth.add_argument("--local-step-seconds", type=float, required=True)
    bandwidth.add_argument("--compression-bits", type=int, default=None)
    bandwidth.set_defaults(func=_cmd_scaling_bandwidth)
    capacity = scaling_sub.add_parser("capacity-plan")
    capacity.add_argument("--price-snapshot", type=Path, required=True)
    capacity.add_argument("--gpu-type", required=True)
    capacity.add_argument("--gpus-per-instance", type=int, required=True)
    capacity.add_argument("--instances", type=int, required=True)
    capacity.add_argument("--hours", type=float, required=True)
    capacity.add_argument("--params", type=int, required=True)
    capacity.add_argument("--bytes-per-param", type=float, required=True)
    capacity.add_argument("--learners", type=int, required=True)
    capacity.add_argument("--expected-tokens-per-second", type=float, required=True)
    capacity.add_argument("--expected-goodput", type=float, required=True)
    capacity.add_argument("--credits", type=float, required=True)
    capacity.add_argument("--allow-sample-prices", action="store_true")
    capacity.add_argument("--allow-stale-prices", action="store_true")
    capacity.add_argument("--allow-ambiguous-price", action="store_true")
    capacity.set_defaults(func=_cmd_scaling_capacity_plan)
    large_state = scaling_sub.add_parser("large-state")
    large_state.add_argument("--params", type=int, required=True)
    large_state.add_argument("--bytes-per-param", type=float, required=True)
    large_state.add_argument("--optimizer-multiplier", type=float, required=True)
    large_state.add_argument("--chunk-size-mb", type=int, required=True)
    large_state.add_argument("--memory-budget-mb", type=int, required=True)
    large_state.add_argument("--learners", type=int, required=True)
    large_state.set_defaults(func=_cmd_scaling_large_state)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
