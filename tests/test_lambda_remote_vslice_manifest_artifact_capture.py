from __future__ import annotations

import json

from lambda_m079s_helpers import learner_syncer_success_artifact
from lambda_m081s_helpers import diloco_success_artifact

from decodilo.dev.diloco_optimizer_smoke import run_diloco_optimizer_smoke
from decodilo.dev.parameter_fragment_smoke import run_parameter_fragment_smoke
from decodilo.lambda_cloud.diloco_artifact_parser import (
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.diloco_optimizer_artifact_parser import (
    DILOCO_OPTIMIZER_SMOKE_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.learner_syncer_smoke_attempt_closeout import (
    LEARNER_SYNCER_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.parameter_fragment_artifact_parser import (
    PARAMETER_FRAGMENT_SMOKE_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
    build_manifest_declared_artifact_capture_from_local_file,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
)


def test_manifest_capture_accepts_runtime_learner_and_diloco_when_manifest_declared(
    tmp_path,
):
    runtime = tmp_path / "runtime.json"
    runtime.write_text(
        json.dumps({"runtime_smoke_status": "passed", "network_used": False}),
        encoding="utf-8",
    )
    learner = tmp_path / "learner.json"
    learner.write_text(json.dumps(learner_syncer_success_artifact()), encoding="utf-8")
    diloco = tmp_path / "diloco.json"
    diloco.write_text(json.dumps(diloco_success_artifact()), encoding="utf-8")
    optimizer = tmp_path / "optimizer.json"
    run_diloco_optimizer_smoke(
        synthetic=True,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
        max_steps=1,
        out=optimizer,
    )
    parameter_fragment = tmp_path / "parameter-fragment.json"
    run_parameter_fragment_smoke(
        synthetic=True,
        fragments=2,
        max_steps=1,
        out=parameter_fragment,
    )

    runtime_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=runtime,
        manifest_declared_paths=[RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH],
    )
    learner_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=LEARNER_SYNCER_DECLARED_ARTIFACT_PATH,
        local_artifact_path=learner,
        manifest_declared_paths=[LEARNER_SYNCER_DECLARED_ARTIFACT_PATH],
    )
    diloco_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=diloco,
        manifest_declared_paths=[DILOCO_SMOKE_DECLARED_ARTIFACT_PATH],
    )
    optimizer_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=DILOCO_OPTIMIZER_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=optimizer,
        manifest_declared_paths=[DILOCO_OPTIMIZER_SMOKE_DECLARED_ARTIFACT_PATH],
    )
    parameter_fragment_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=PARAMETER_FRAGMENT_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=parameter_fragment,
        manifest_declared_paths=[PARAMETER_FRAGMENT_SMOKE_DECLARED_ARTIFACT_PATH],
    )

    assert runtime_capture.capture_succeeded is True
    assert learner_capture.parse_status == "parsed_safe_learner_syncer_smoke_artifact"
    assert diloco_capture.parse_status == "parsed_safe_diloco_smoke_artifact"
    assert diloco_capture.parsed_summary["optimization_fidelity"] == (
        "diloco_shaped_protocol_only"
    )
    assert (
        optimizer_capture.parse_status
        == "parsed_safe_diloco_optimizer_smoke_artifact"
    )
    assert optimizer_capture.parsed_summary["optimization_fidelity"] == (
        "optimizer_semantics_smoke"
    )
    assert optimizer_capture.parsed_summary["inner_optimizer_semantics"] == "adamw"
    assert optimizer_capture.parsed_summary["outer_optimizer_semantics"] == "nesterov"
    assert (
        parameter_fragment_capture.parse_status
        == "parsed_safe_parameter_fragment_smoke_artifact"
    )
    assert (
        parameter_fragment_capture.parsed_summary["parameter_fragment_semantics"]
        == "synthetic_vector_fragments"
    )
    assert parameter_fragment_capture.parsed_summary["fragment_count"] == 2


def test_manifest_capture_rejects_undeclared_directory_glob_and_traversal(tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}", encoding="utf-8")
    directory = tmp_path / "dir"
    directory.mkdir()

    undeclared = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=artifact,
        manifest_declared_paths=[RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH],
    )
    directory_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=directory,
        manifest_declared_paths=[DILOCO_SMOKE_DECLARED_ARTIFACT_PATH],
    )
    glob_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path="/tmp/decodilo-*.json",
        local_artifact_path=artifact,
        manifest_declared_paths=["/tmp/decodilo-*.json"],
    )
    traversal_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path="/tmp/../secret.json",
        local_artifact_path=artifact,
        manifest_declared_paths=["/tmp/../secret.json"],
    )

    assert undeclared.content_capture_status == "blocked_undeclared_artifact_path"
    assert "undeclared_artifact_path" in undeclared.blockers
    assert directory_capture.content_capture_status == "blocked_artifact_path_not_file"
    assert "artifact_path_not_file" in directory_capture.blockers
    assert glob_capture.content_capture_status == "blocked_undeclared_artifact_path"
    assert traversal_capture.content_capture_status == "blocked_undeclared_artifact_path"


def test_manifest_capture_rejects_symlink_escape_when_possible(tmp_path):
    target = tmp_path / "target.json"
    target.write_text(json.dumps(diloco_success_artifact()), encoding="utf-8")
    symlink = tmp_path / "link.json"
    symlink.symlink_to(target)

    capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=symlink,
        manifest_declared_paths=[DILOCO_SMOKE_DECLARED_ARTIFACT_PATH],
    )

    assert capture.content_capture_status == "blocked_artifact_symlink_escape"
    assert "artifact_symlink_escape_rejected" in capture.blockers


def test_manifest_capture_suppresses_secret_body_and_bounds_oversized(tmp_path):
    secret = diloco_success_artifact()
    secret["safe_error_message"] = "Authorization: Bearer abcdefghijklmnop123456"
    secret_artifact = tmp_path / "secret.json"
    secret_artifact.write_text(json.dumps(secret), encoding="utf-8")
    oversized = tmp_path / "oversized.json"
    oversized.write_text(json.dumps({"x": "a" * 64}), encoding="utf-8")

    secret_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=secret_artifact,
        manifest_declared_paths=[DILOCO_SMOKE_DECLARED_ARTIFACT_PATH],
    )
    oversized_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=oversized,
        manifest_declared_paths=[DILOCO_SMOKE_DECLARED_ARTIFACT_PATH],
        max_content_bytes=16,
    )

    assert secret_capture.capture_succeeded is True
    assert secret_capture.body_persisted is False
    assert secret_capture.parsed_summary_persisted is True
    assert secret_capture.parsed_summary["safe_error_message"] == "<redacted>"
    assert oversized_capture.capture_succeeded is True
    assert oversized_capture.content_capture_status == "metadata_only"
    assert oversized_capture.artifact_sha256 is not None


def test_manifest_capture_handles_command_failure_artifact_and_absent_artifact(tmp_path):
    failed = diloco_success_artifact()
    failed.update(
        {
            "diloco_smoke_status": "failed",
            "failed_check": "diloco_shape_check",
            "error_classification": "synthetic_protocol_mismatch",
            "safe_error_message": "bounded synthetic mismatch",
        }
    )
    failure_artifact = tmp_path / "failed.json"
    failure_artifact.write_text(json.dumps(failed), encoding="utf-8")

    failure_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=failure_artifact,
        manifest_declared_paths=[DILOCO_SMOKE_DECLARED_ARTIFACT_PATH],
    )
    absent_capture = build_manifest_declared_artifact_capture_from_local_file(
        declared_remote_path=DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=tmp_path / "missing.json",
        manifest_declared_paths=[DILOCO_SMOKE_DECLARED_ARTIFACT_PATH],
    )

    assert failure_capture.capture_succeeded is True
    assert failure_capture.parsed_summary["diloco_smoke_status"] == "failed"
    assert failure_capture.parsed_summary["failed_check"] == "diloco_shape_check"
    assert absent_capture.capture_succeeded is False
    assert absent_capture.content_capture_status == "artifact_absent"
