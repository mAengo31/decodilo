from __future__ import annotations

import json

from lambda_m079s_helpers import learner_syncer_success_artifact, write_m079r_manifest

from decodilo.lambda_cloud.learner_syncer_artifact_parser import (
    parse_learner_syncer_artifact_file,
)
from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
    build_lambda_remote_vslice_declared_artifact_policy_from_path,
    write_lambda_remote_vslice_declared_artifact_policy,
)


def _policy_path(tmp_path):
    manifest = write_m079r_manifest(tmp_path / "manifest.json")
    policy_path = tmp_path / "policy.json"
    write_lambda_remote_vslice_declared_artifact_policy(
        policy_path,
        build_lambda_remote_vslice_declared_artifact_policy_from_path(
            manifest=manifest,
        ),
    )
    return policy_path


def test_learner_syncer_artifact_parser_persists_safe_body_and_summary(tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text(json.dumps(learner_syncer_success_artifact()), encoding="utf-8")

    report = parse_learner_syncer_artifact_file(
        artifact_path=artifact,
        policy=_policy_path(tmp_path),
    )

    assert report.parse_status == "parsed_safe_learner_syncer_smoke_artifact"
    assert report.raw_content_persisted is True
    assert report.parsed_summary_persisted is True
    assert report.safe_artifact_body["learner_syncer_smoke_status"] == "passed"
    assert report.parsed_summary["learner_syncer_exchange_check_passed"] is True
    assert report.secret_scan_passed is True


def test_learner_syncer_artifact_parser_suppresses_secret_body_but_keeps_summary(tmp_path):
    artifact = tmp_path / "artifact.json"
    body = learner_syncer_success_artifact() | {
        "safe_error_message": "Authorization: Bearer abcdefghijklmnopqrstu",
    }
    artifact.write_text(json.dumps(body), encoding="utf-8")

    report = parse_learner_syncer_artifact_file(
        artifact_path=artifact,
        policy=_policy_path(tmp_path),
    )

    assert report.parse_status == "parsed_redacted_learner_syncer_smoke_artifact"
    assert report.raw_content_persisted is False
    assert report.parsed_summary_persisted is True
    assert report.safe_artifact_body is None
    assert report.parsed_summary["safe_error_message"] == "<redacted>"


def test_learner_syncer_artifact_parser_rejects_non_json_and_metadata_only_oversized(
    tmp_path,
):
    policy = build_lambda_remote_vslice_declared_artifact_policy_from_path(
        manifest=write_m079r_manifest(tmp_path / "manifest.json"),
    ).model_copy(update={"max_content_bytes": 8})
    non_json = tmp_path / "bad.json"
    non_json.write_text("not json", encoding="utf-8")
    oversized = tmp_path / "large.json"
    oversized.write_text(json.dumps(learner_syncer_success_artifact()), encoding="utf-8")

    non_json_report = parse_learner_syncer_artifact_file(
        artifact_path=non_json,
        policy=policy,
    )
    oversized_report = parse_learner_syncer_artifact_file(
        artifact_path=oversized,
        policy=policy,
    )

    assert non_json_report.parse_status == "rejected_non_json"
    assert oversized_report.parse_status == "metadata_only_oversized"
    assert oversized_report.artifact_sha256 is not None
