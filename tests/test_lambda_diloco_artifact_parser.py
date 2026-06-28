from __future__ import annotations

import json

from lambda_m081s_helpers import diloco_success_artifact

from decodilo.lambda_cloud.diloco_artifact_parser import (
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
    parse_diloco_artifact_file,
)


def test_diloco_artifact_parser_persists_safe_summary_without_overclaim(tmp_path):
    artifact = tmp_path / "decodilo-diloco-smoke.json"
    artifact.write_text(json.dumps(diloco_success_artifact()), encoding="utf-8")

    report = parse_diloco_artifact_file(
        artifact_path=artifact,
        policy={"declared_artifact_path": DILOCO_SMOKE_DECLARED_ARTIFACT_PATH},
    )

    assert report.parse_status == "parsed_safe_diloco_smoke_artifact"
    assert report.raw_content_persisted is True
    assert report.parsed_summary_persisted is True
    assert report.parsed_summary["optimization_fidelity"] == "diloco_shaped_protocol_only"
    assert report.parsed_summary["inner_optimizer_semantics"] == "synthetic_placeholder"
    assert report.parsed_summary["outer_optimizer_semantics"] == "token_weighted_merge"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_diloco_artifact_parser_redacts_secret_body_but_keeps_summary(tmp_path):
    payload = diloco_success_artifact()
    payload["safe_error_message"] = "Authorization: Bearer abcdefghijklmnop123456"
    artifact = tmp_path / "decodilo-diloco-smoke.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    report = parse_diloco_artifact_file(
        artifact_path=artifact,
        policy={"declared_artifact_path": DILOCO_SMOKE_DECLARED_ARTIFACT_PATH},
    )

    assert report.parse_status == "parsed_redacted_diloco_smoke_artifact"
    assert report.secret_scan_passed is False
    assert report.raw_content_persisted is False
    assert report.parsed_summary_persisted is True
    assert report.parsed_summary["safe_error_message"] == "<redacted>"


def test_diloco_artifact_parser_rejects_non_json_and_bounds_oversized(tmp_path):
    non_json = tmp_path / "bad.json"
    non_json.write_text("not json", encoding="utf-8")
    oversized = tmp_path / "oversized.json"
    oversized.write_text(json.dumps({"x": "a" * 64}), encoding="utf-8")

    rejected = parse_diloco_artifact_file(
        artifact_path=non_json,
        policy={"declared_artifact_path": DILOCO_SMOKE_DECLARED_ARTIFACT_PATH},
    )
    bounded = parse_diloco_artifact_file(
        artifact_path=oversized,
        policy={
            "declared_artifact_path": DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
            "max_content_bytes": 16,
        },
    )

    assert rejected.parse_status == "rejected_non_json"
    assert "artifact_json_parse_failed" in rejected.blockers
    assert bounded.parse_status == "metadata_only_oversized"
    assert bounded.artifact_sha256 is not None
    assert bounded.raw_content_persisted is False
