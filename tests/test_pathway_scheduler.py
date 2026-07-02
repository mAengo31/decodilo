from __future__ import annotations

import pytest

from decodilo.operation.pathway_scheduler import (
    PathwayArtifactFuture,
    PathwayResourcePolicy,
    PathwayScheduler,
    PathwaySchedulerError,
    PathwayTask,
)


def test_pathway_scheduler_runs_dag_with_artifact_futures_and_retries() -> None:
    attempts = {"train": 0}
    scheduler = PathwayScheduler(resource_policy=PathwayResourcePolicy(local_only=True))
    scheduler.add_task(
        PathwayTask(
            task_id="prepare",
            op="prepare_data",
            produces=["dataset"],
            run=lambda ctx: {"dataset": {"tokens": 128}},
        )
    )

    def train(ctx):
        attempts["train"] += 1
        if attempts["train"] == 1:
            raise RuntimeError("transient gpu warmup")
        dataset = ctx.resolve("dataset")
        return {"checkpoint": {"tokens": dataset["tokens"], "loss": 1.25}}

    scheduler.add_task(
        PathwayTask(
            task_id="train",
            op="local_train",
            depends_on=["prepare"],
            consumes=["dataset"],
            produces=["checkpoint"],
            max_attempts=2,
            run=train,
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="validate",
            op="validate_metrics",
            depends_on=["train"],
            consumes=["checkpoint"],
            produces=["report"],
            run=lambda ctx: {"report": {"passed": ctx.resolve("checkpoint")["loss"] < 2.0}},
        )
    )

    result = scheduler.run()

    assert result.status == "completed"
    assert result.execution_order == ["prepare", "train", "validate"]
    assert result.task_attempts == {"prepare": 1, "train": 2, "validate": 1}
    assert result.artifacts["report"].value == {"passed": True}
    assert all(isinstance(value, PathwayArtifactFuture) for value in result.artifacts.values())
    assert result.launch_ready is False
    assert result.launch_allowed is False
    assert result.production_scale_ready is False


def test_pathway_scheduler_rejects_cycles_and_missing_dependencies() -> None:
    scheduler = PathwayScheduler(resource_policy=PathwayResourcePolicy(local_only=True))
    scheduler.add_task(PathwayTask(task_id="a", op="a", depends_on=["b"], run=lambda ctx: {}))
    scheduler.add_task(PathwayTask(task_id="b", op="b", depends_on=["a"], run=lambda ctx: {}))

    with pytest.raises(PathwaySchedulerError, match="cycle"):
        scheduler.run()

    scheduler = PathwayScheduler(resource_policy=PathwayResourcePolicy(local_only=True))
    scheduler.add_task(PathwayTask(task_id="a", op="a", depends_on=["missing"], run=lambda ctx: {}))
    with pytest.raises(PathwaySchedulerError, match="missing dependency"):
        scheduler.run()


def test_pathway_scheduler_fails_closed_for_remote_tasks_without_launch_permission() -> None:
    scheduler = PathwayScheduler(resource_policy=PathwayResourcePolicy(local_only=True))
    scheduler.add_task(
        PathwayTask(
            task_id="lambda_train",
            op="lambda_train",
            remote=True,
            run=lambda ctx: {},
        )
    )

    with pytest.raises(PathwaySchedulerError, match="remote task blocked"):
        scheduler.run()


def test_pathway_scheduler_can_wrap_real_local_operation_backend(tmp_path) -> None:
    from decodilo.operation import OperationSpec, run_operation

    scheduler = PathwayScheduler(resource_policy=PathwayResourcePolicy(local_only=True))
    spec = OperationSpec(steps=12, syncer_checkpoint_interval_rounds=1)
    scheduler.add_task(
        PathwayTask(
            task_id="compile_spec",
            op="compile_operation_spec",
            produces=["operation_spec"],
            run=lambda ctx: {"operation_spec": spec},
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="run_local_diloco",
            op="run_local_backend",
            depends_on=["compile_spec"],
            consumes=["operation_spec"],
            produces=["operation_result"],
            run=lambda ctx: {
                "operation_result": run_operation(
                    ctx.resolve("operation_spec"),
                    workdir=tmp_path / "runtime",
                )
            },
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="validate_result",
            op="validate_operation_result",
            depends_on=["run_local_diloco"],
            consumes=["operation_result"],
            produces=["validation_report"],
            run=lambda ctx: {
                "validation_report": {
                    "passed": ctx.resolve("operation_result").status == "completed",
                    "sync_rounds": ctx.resolve("operation_result").sync_rounds_committed,
                    "replay_passed": ctx.resolve("operation_result").replay_passed,
                }
            },
        )
    )

    result = scheduler.run()

    report = result.artifacts["validation_report"].value
    operation_result = result.artifacts["operation_result"].value
    assert result.execution_order == ["compile_spec", "run_local_diloco", "validate_result"]
    assert report["passed"] is True
    assert report["sync_rounds"] >= 1
    assert report["replay_passed"] is True
    assert operation_result.inner_optimizer_semantics == "adamw"
    assert operation_result.outer_optimizer_semantics == "nesterov"
    assert result.launch_ready is False
    assert result.launch_allowed is False
