from __future__ import annotations

from lambda_m051_helpers import RAW_TEST_SSH_KEY_NAME, write_m051_inputs

from decodilo.lambda_cloud.m051_arming_command_preview import (
    build_lambda_m051_arming_command_preview_from_paths,
)


def test_m051_arming_command_preview_ready_and_non_executable(tmp_path):
    paths = write_m051_inputs(tmp_path)

    preview = build_lambda_m051_arming_command_preview_from_paths(
        arming_gate=paths["arming_gate_m051"],
    )

    assert preview.preview_status == "ready_for_future_m051b_one_shot_metadata_bootstrap"
    assert preview.executable is False
    assert preview.statement == "M051A does not execute this command."
    assert "--m051-one-shot-arming" in preview.command_preview
    assert "--m051-reviewer-bridge" in preview.command_preview
    assert RAW_TEST_SSH_KEY_NAME not in " ".join(preview.command_preview)
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
