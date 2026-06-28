from __future__ import annotations

from lambda_m064_helpers import write_m064_chain

from decodilo.lambda_cloud.m065_python_runtime_runbook_preview import (
    build_lambda_m065_python_runtime_runbook_preview_from_path,
)


def test_m065_python_runtime_runbook_preview_is_non_executable(tmp_path):
    paths = write_m064_chain(tmp_path)

    preview = build_lambda_m065_python_runtime_runbook_preview_from_path(
        authorization=paths["authorization"],
    )

    assert preview.preview_status == "ready_for_future_m065_python_version_query_review"
    assert preview.executable is False
    assert preview.selected_command == "python3 --version"
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
