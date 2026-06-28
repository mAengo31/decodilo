from __future__ import annotations

from lambda_m092_helpers import write_m091_report

from decodilo.lambda_cloud.tiny_real_training_readiness import (
    build_lambda_tiny_real_training_readiness_from_path,
)


def test_tiny_real_training_readiness_follows_m091_branch(tmp_path):
    readiness = build_lambda_tiny_real_training_readiness_from_path(
        m091_report=write_m091_report(tmp_path),
    )

    assert readiness.readiness_status == "ready_for_future_tiny_real_training_planning"
    assert readiness.scaffold_completion_status == "complete"
    assert readiness.bounded_synthetic_experiment_completed is True
    assert readiness.next_branch == "plan_tiny_real_training_smoke"
    assert readiness.launch_ready is False
    assert readiness.launch_allowed is False
