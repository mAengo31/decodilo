from __future__ import annotations

from decodilo.dev.integrated_diloco_smoke import run_integrated_diloco_smoke
from decodilo.lambda_cloud.integrated_diloco_artifact_parser import (
    INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.remote_dependency_bundle import (
    build_lambda_m068r_dependency_bundle_default_manifest,
)
from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    LambdaRemoteVerticalSliceOneShotArming,
    build_lambda_remote_vertical_slice_policy,
    build_lambda_remote_vertical_slice_reviewer_bridge_from_path,
    validate_lambda_remote_vertical_slice_manifest_from_paths,
    write_lambda_remote_vertical_slice_command_manifest,
    write_lambda_remote_vertical_slice_one_shot_arming,
    write_lambda_remote_vertical_slice_policy,
)
from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
    build_lambda_remote_vslice_manifest_artifact_policy_from_path,
    build_manifest_declared_artifact_capture_from_local_file,
)


def test_m085r_default_manifest_is_exact_integrated_smoke(tmp_path):
    policy_path = tmp_path / "policy.json"
    manifest_path = tmp_path / "manifest.json"
    write_lambda_remote_vertical_slice_policy(
        policy_path,
        build_lambda_remote_vertical_slice_policy(),
    )
    manifest = build_lambda_m068r_dependency_bundle_default_manifest(milestone="M085R")
    write_lambda_remote_vertical_slice_command_manifest(manifest_path, manifest)

    validation = validate_lambda_remote_vertical_slice_manifest_from_paths(
        manifest=manifest_path,
        policy=policy_path,
    )
    stages = [entry.stage for entry in manifest.command_entries]

    assert validation.validation_passed is True
    assert manifest.milestone == "M085R"
    assert manifest.max_remote_commands == 11
    assert stages[-1] == "integrated_diloco_smoke_command"
    assert manifest.command_entries[1].argv_tokens == [
        "sha256sum",
        "/tmp/decodilo-source-bundle-m085r.tar.gz",
    ]
    assert manifest.command_entries[-1].argv_tokens == [
        "env",
        "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "integrated-diloco-smoke",
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "1",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
        "--out",
        INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
    ]


def test_m085r_manifest_artifact_policy_accepts_integrated_declared_path(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest = build_lambda_m068r_dependency_bundle_default_manifest(milestone="M085R")
    write_lambda_remote_vertical_slice_command_manifest(manifest_path, manifest)

    policy = build_lambda_remote_vslice_manifest_artifact_policy_from_path(
        manifest=manifest_path,
    )

    assert policy.policy_status == "manifest_artifact_policy_defined"
    assert policy.declared_artifact_path == INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH
    assert policy.integrated_diloco_smoke_declared_artifact_supported is True
    assert policy.no_arbitrary_file_reads is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_m085r_manifest_capture_parses_integrated_smoke_artifact(tmp_path):
    artifact = tmp_path / "integrated.json"
    run_integrated_diloco_smoke(
        synthetic=True,
        learners=1,
        sync_rounds=1,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
        max_steps=1,
        out=artifact,
    )

    capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=artifact,
        manifest_declared_paths=[INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH],
    )

    assert capture.capture_succeeded is True
    assert capture.body_persisted is True
    assert capture.parsed_summary_persisted is True
    assert capture.parse_status == "parsed_safe_integrated_diloco_smoke_artifact"
    assert capture.parsed_summary["integrated_diloco_smoke_status"] == "passed"
    assert (
        capture.parsed_summary["optimization_fidelity"]
        == "integrated_optimizer_protocol_smoke"
    )
    assert capture.parsed_summary["inner_optimizer_semantics"] == "adamw"
    assert capture.parsed_summary["outer_optimizer_semantics"] == "nesterov"
    assert capture.parsed_summary["parameter_fragment_semantics"] == "not_exercised"


def test_m085r_one_shot_arming_and_reviewer_bridge_are_supported(tmp_path):
    arming_path = tmp_path / "arming.json"
    arming = LambdaRemoteVerticalSliceOneShotArming(
        arming_id="m085r-test",
        arming_status="armed_for_one_shot_m085r_integrated_diloco_smoke",
        armed_for="m085r_integrated_diloco_smoke_single_launch_attempt",
        selected_candidate="gpu_1x_a10",
        selected_region="us-west-1",
        command_manifest_hash="1" * 64,
        source_bundle_sha256="2" * 64,
        dependency_bundle_sha256="3" * 64,
        declared_artifact_policy_hash="4" * 64,
        max_remote_command_attempts=11,
        max_uploaded_bundles=2,
        single_source_bundle_upload_allowed=True,
        created_at_utc="2026-01-01T00:00:00+00:00",
        expires_at_utc="2099-01-01T00:00:00+00:00",
    )
    write_lambda_remote_vertical_slice_one_shot_arming(arming_path, arming)

    bridge = build_lambda_remote_vertical_slice_reviewer_bridge_from_path(
        arming=arming_path,
        now_utc="2026-01-01T00:00:01+00:00",
    )

    assert bridge.bridge_status == "reviewer_compatible_one_shot_ready"
    assert bridge.declared_artifact_policy_hash == "4" * 64
    assert bridge.launch_ready is False
    assert bridge.launch_allowed is False
