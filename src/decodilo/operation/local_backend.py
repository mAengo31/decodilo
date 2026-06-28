"""Local operation backend that delegates to the real learner/syncer runtime."""

from __future__ import annotations

from pathlib import Path

from decodilo.operation.result import OperationResult
from decodilo.operation.spec import OperationSafetyEnvelope, OperationSpec
from decodilo.runtime.local_runner import LocalRunConfig, LocalRunner


class LocalOperationBackend:
    """Runs an operation on the local multiprocess learner/syncer runtime.

    This backend does not reimplement training. It builds a ``LocalRunConfig``
    and executes the real ``LocalRunner``, then normalizes the resulting
    ``LocalRuntimeReport`` into an ``OperationResult``.
    """

    name = "local"

    def run(self, spec: OperationSpec, *, workdir: Path) -> OperationResult:
        workdir.mkdir(parents=True, exist_ok=True)
        report_json = workdir / "report.json"
        config = LocalRunConfig(
            learners=spec.learners,
            steps=spec.steps,
            min_quorum=spec.min_quorum,
            seed=spec.seed,
            workdir=workdir,
            report_json=report_json,
            vector_dim=spec.vector_dim,
            fragments=spec.fragments,
            local_steps_per_sync=spec.local_steps_per_sync,
            outer_optimizer=spec.outer_optimizer,
            outer_lr=spec.outer_lr,
            outer_momentum=spec.outer_momentum,
            trainer_type=spec.trainer_type,
            trainer_config=dict(spec.trainer_config),
            heartbeat_timeout_seconds=2.0,
            syncer_checkpoint_interval_rounds=spec.syncer_checkpoint_interval_rounds,
            restart_syncer_after_round=spec.restart_syncer_after_round,
        )
        report = LocalRunner(config).run()
        report_dict = report.model_dump(mode="json")
        metrics = report_dict.get("metrics", {})
        replay = report_dict.get("replay_validation", {})
        metric_validation = report_dict.get("metric_validation", {})
        events_path = workdir / "events.jsonl"
        syncer_recovered = False
        if events_path.exists():
            syncer_recovered = "syncer_recovered" in events_path.read_text(encoding="utf-8")

        # Re-assert the fail-closed safety envelope from the live report.
        safety = OperationSafetyEnvelope(
            launch_ready=bool(report_dict.get("launch_ready", False)),
            launch_allowed=bool(report_dict.get("launch_allowed", False)),
            billable_action_performed=bool(report_dict.get("billable_action_performed", False)),
            remote_backend_enabled=bool(report_dict.get("remote_backend_enabled", False)),
            network_scope=str(report_dict.get("network_scope", "localhost_only")),
        )

        return OperationResult(
            operation_name=spec.name,
            backend=self.name,
            status="completed",
            inner_optimizer_semantics=metrics.get("inner_optimizer_semantics"),
            outer_optimizer_semantics=metrics.get("outer_optimizer_semantics"),
            outer_momentum=metrics.get("outer_momentum"),
            learners=len(report_dict.get("process_summary", {}).get("learner_pids", {})),
            final_global_version=int(report_dict.get("final_global_version", 0)),
            sync_rounds_committed=int(metrics.get("sync_rounds_committed", 0)),
            trainer_final_loss=report_dict.get("trainer_final_loss"),
            training_attempted=bool(metrics.get("training_attempted", False)),
            real_training_mechanics_exercised=bool(
                metrics.get("real_training_mechanics_exercised", False)
            ),
            optimizer_state_present=bool(metrics.get("optimizer_state_present", False)),
            nesterov_outer_optimizer_exercised=bool(
                metrics.get("nesterov_outer_optimizer_exercised", False)
            ),
            outer_optimizer_semantics_checked=bool(
                metrics.get("outer_optimizer_semantics_checked", False)
            ),
            pseudo_gradient_numeric_check_passed=metrics.get(
                "pseudo_gradient_numeric_check_passed"
            ),
            pseudo_gradient_numeric_check_reason=metrics.get(
                "pseudo_gradient_numeric_check_reason"
            ),
            pseudo_gradient_numeric_rounds_checked=int(
                metrics.get("pseudo_gradient_numeric_rounds_checked", 0)
            ),
            pseudo_gradient_check_passed=metrics.get("pseudo_gradient_check_passed"),
            replay_passed=bool(replay.get("replay_passed", False)),
            metric_validation_passed=bool(metric_validation.get("passed", False)),
            syncer_recovered=syncer_recovered,
            safety=safety,
            backend_report={
                "report_json_path": str(report_json),
                "run_id": report_dict.get("run_id"),
                "mode": report_dict.get("mode"),
            },
        )
