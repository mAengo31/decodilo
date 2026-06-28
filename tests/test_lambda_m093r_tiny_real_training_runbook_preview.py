from __future__ import annotations

from lambda_m092_helpers import write_m092_chain

from decodilo.lambda_cloud.m093r_tiny_real_training_runbook_preview import (
    build_lambda_m093r_tiny_real_training_runbook_preview_from_path,
)


def test_m093r_tiny_real_training_runbook_preview_is_non_executable(tmp_path):
    paths = write_m092_chain(tmp_path)

    preview = build_lambda_m093r_tiny_real_training_runbook_preview_from_path(
        authorization=paths["authorization"],
    )

    assert preview.preview_status == "ready_for_future_m093r_tiny_real_training_review"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
    assert preview.billable_action_performed is False
    assert any("tiny-real-training-smoke" in item for item in preview.future_requirements)
