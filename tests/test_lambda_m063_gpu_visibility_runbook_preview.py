from __future__ import annotations

from lambda_m062_helpers import write_m062_chain

from decodilo.lambda_cloud.m063_gpu_visibility_runbook_preview import (
    build_lambda_m063_gpu_visibility_runbook_preview_from_path,
)


def test_m063_gpu_visibility_runbook_preview_ready_and_non_executable(tmp_path):
    paths = write_m062_chain(tmp_path)

    runbook = build_lambda_m063_gpu_visibility_runbook_preview_from_path(
        authorization=paths["authorization"],
    )

    assert runbook.preview_status == "ready_for_future_m063_gpu_visibility_query_review"
    assert runbook.executable is False
    assert runbook.package_install_allowed is False
    assert runbook.training_allowed is False
    assert runbook.launch_ready is False
    assert runbook.launch_allowed is False
