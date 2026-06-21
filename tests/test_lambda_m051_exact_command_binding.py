from __future__ import annotations

from lambda_m051_helpers import RAW_TEST_SSH_KEY_NAME, write_m051_inputs

from decodilo.lambda_cloud.m051_exact_command_binding import (
    build_lambda_m051_exact_command_binding_from_paths,
)


def test_m051_exact_command_binding_contains_required_arming_flags(tmp_path):
    paths = write_m051_inputs(tmp_path)

    report = build_lambda_m051_exact_command_binding_from_paths(
        arming=paths["one_shot_arming_m051"],
    )

    assert report.binding_passed is True
    assert report.command_contains_required_flags is True
    assert report.command_contains_forbidden_flags is False
    assert "--m051-one-shot-arming" in report.command_preview
    assert "--m051-reviewer-bridge" in report.command_preview
    assert "--m051-artifact-binding" in report.command_preview
    assert "--m051-arming-gate" in report.command_preview
    assert RAW_TEST_SSH_KEY_NAME not in " ".join(report.command_preview)
    assert report.executable is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m051_exact_command_binding_blocks_unarmed_artifact(tmp_path):
    paths = write_m051_inputs(tmp_path, include_candidate=False)

    report = build_lambda_m051_exact_command_binding_from_paths(
        arming=paths["one_shot_arming_m051"],
    )

    assert report.binding_passed is False
    assert report.blockers
