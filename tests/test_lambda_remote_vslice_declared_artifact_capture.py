from __future__ import annotations

import json

from decodilo.lambda_cloud.remote_vslice_declared_artifact_capture import (
    LEARNER_SYNCER_SMOKE_DECLARED_ARTIFACT_PATH,
    build_declared_artifact_capture_from_local_file,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
)


def test_declared_artifact_capture_persists_safe_body_on_failure(tmp_path):
    artifact = tmp_path / "decodilo-runtime-smoke.json"
    artifact.write_text(
        json.dumps(
            {
                "runtime_smoke_status": "failed",
                "failed_check": "protocol",
                "error_classification": "protocol_mismatch",
                "safe_error_message": "synthetic mismatch",
                "network_used": False,
            }
        ),
        encoding="utf-8",
    )

    capture = build_declared_artifact_capture_from_local_file(
        declared_remote_path=RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=artifact,
    )

    assert capture.capture_succeeded is True
    assert capture.body_capture_succeeded is True
    assert capture.body_persisted is True
    assert capture.parsed_summary_persisted is True
    assert capture.safe_artifact_body["runtime_smoke_status"] == "failed"
    assert capture.content_capture_status == "body_persisted"


def test_declared_artifact_capture_rejects_undeclared_and_directory_paths(tmp_path):
    artifact = tmp_path / "decodilo-runtime-smoke.json"
    artifact.write_text("{}", encoding="utf-8")
    directory = tmp_path / "dir"
    directory.mkdir()

    wrong_path = build_declared_artifact_capture_from_local_file(
        declared_remote_path="/tmp/other.json",
        local_artifact_path=artifact,
    )
    directory_capture = build_declared_artifact_capture_from_local_file(
        declared_remote_path=RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=directory,
    )

    assert wrong_path.capture_succeeded is False
    assert "undeclared_artifact_path" in wrong_path.blockers
    assert directory_capture.capture_succeeded is False
    assert "artifact_path_not_file" in directory_capture.blockers


def test_declared_artifact_capture_keeps_oversized_artifact_metadata_only(tmp_path):
    artifact = tmp_path / "decodilo-runtime-smoke.json"
    artifact.write_text("{" + "\"x\":\"" + ("a" * 64) + "\"}", encoding="utf-8")

    capture = build_declared_artifact_capture_from_local_file(
        declared_remote_path=RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=artifact,
        max_content_bytes=16,
    )

    assert capture.capture_succeeded is True
    assert capture.artifact_exists is True
    assert capture.artifact_sha256 is not None
    assert capture.body_persisted is False
    assert capture.parsed_summary_persisted is False
    assert capture.content_capture_status == "metadata_only"


def test_declared_artifact_capture_accepts_learner_syncer_declared_artifact(tmp_path):
    artifact = tmp_path / "decodilo-learner-syncer-smoke.json"
    artifact.write_text(
        json.dumps(
            {
                "learner_syncer_smoke_status": "passed",
                "learner_check_passed": True,
                "syncer_check_passed": True,
                "learner_syncer_exchange_check_passed": True,
                "update_or_commit_check_passed": True,
                "replay_or_metric_check_passed": True,
                "network_used": False,
                "download_attempted": False,
                "training_attempted": False,
            }
        ),
        encoding="utf-8",
    )

    capture = build_declared_artifact_capture_from_local_file(
        declared_remote_path=LEARNER_SYNCER_SMOKE_DECLARED_ARTIFACT_PATH,
        local_artifact_path=artifact,
    )

    assert capture.capture_succeeded is True
    assert capture.body_persisted is True
    assert capture.parsed_summary_persisted is True
    assert capture.safe_artifact_body["learner_syncer_smoke_status"] == "passed"
    assert capture.parse_status == "parsed_safe_learner_syncer_smoke_artifact"
