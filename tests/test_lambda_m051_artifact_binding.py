from __future__ import annotations

from lambda_m051_helpers import write_m051_inputs

from decodilo.lambda_cloud.m051_artifact_binding import (
    build_lambda_m051_artifact_binding_from_paths,
)


def test_m051_artifact_binding_passes_complete_fixture(tmp_path):
    paths = write_m051_inputs(tmp_path)

    report = build_lambda_m051_artifact_binding_from_paths(
        arming=paths["one_shot_arming_m051"],
        command_binding=paths["command_binding_m051"],
    )

    assert report.binding_passed is True
    assert "metadata_plan" in report.artifact_hashes
    assert report.command_hash
    assert report.missing_items == []
    assert report.hash_mismatches == []
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m051_artifact_binding_blocks_hash_mismatch(tmp_path):
    paths = write_m051_inputs(tmp_path)
    paths["metadata_plan"].write_text('{"tampered": true}\n', encoding="utf-8")

    report = build_lambda_m051_artifact_binding_from_paths(
        arming=paths["one_shot_arming_m051"],
        command_binding=paths["command_binding_m051"],
    )

    assert report.binding_passed is False
    assert "metadata_plan" in report.hash_mismatches
