from __future__ import annotations

import json

from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
    parse_runtime_smoke_artifact_file,
)


def _policy(max_bytes: int = 32768) -> dict:
    return {
        "declared_artifact_path": RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
        "max_content_bytes": max_bytes,
    }


def test_parser_persists_safe_failure_body_and_summary(tmp_path):
    artifact = tmp_path / "runtime-smoke.json"
    artifact.write_text(
        json.dumps(
            {
                "runtime_smoke_status": "failed",
                "failed_check": "replay_metric",
                "error_classification": "assertion_failed",
                "safe_error_message": "metric mismatch",
                "network_used": False,
                "package_install_attempted": False,
                "download_attempted": False,
                "training_attempted": False,
                "torch_required": False,
                "gpu_required": False,
                "background_process_started": False,
                "elapsed_seconds": 0.01,
            }
        ),
        encoding="utf-8",
    )

    report = parse_runtime_smoke_artifact_file(
        artifact_path=artifact,
        policy=_policy(),
    )

    assert report.parse_status == "parsed_safe_runtime_smoke_artifact"
    assert report.raw_content_persisted is True
    assert report.safe_artifact_body is not None
    assert report.parsed_summary_persisted is True
    assert report.parsed_summary["runtime_smoke_status"] == "failed"
    assert report.parsed_summary["failed_check"] == "replay_metric"
    assert report.secret_scan_passed is True


def test_parser_redacts_secret_content_and_skips_raw_body(tmp_path):
    artifact = tmp_path / "runtime-smoke-secret.json"
    artifact.write_text(
        json.dumps(
            {
                "runtime_smoke_status": "failed",
                "failed_check": "runtime",
                "error_classification": "unsafe_error",
                "safe_error_message": "Authorization: Bearer abcdefghijklmnop",
                "network_used": False,
            }
        ),
        encoding="utf-8",
    )

    report = parse_runtime_smoke_artifact_file(
        artifact_path=artifact,
        policy=_policy(),
    )

    assert report.parse_status == "parsed_redacted_runtime_smoke_artifact"
    assert report.secret_scan_passed is False
    assert report.raw_content_persisted is False
    assert report.safe_artifact_body is None
    assert report.parsed_summary_persisted is True
    assert "<redacted>" in report.parsed_summary["safe_error_message"]


def test_parser_rejects_non_json_and_bounds_oversized_content(tmp_path):
    non_json = tmp_path / "not-json.txt"
    non_json.write_text("not json", encoding="utf-8")
    oversized = tmp_path / "oversized.json"
    oversized.write_text("{" + "\"x\":\"" + ("a" * 64) + "\"}", encoding="utf-8")

    non_json_report = parse_runtime_smoke_artifact_file(
        artifact_path=non_json,
        policy=_policy(),
    )
    oversized_report = parse_runtime_smoke_artifact_file(
        artifact_path=oversized,
        policy=_policy(max_bytes=16),
    )

    assert non_json_report.parse_status == "rejected_non_json"
    assert non_json_report.raw_content_persisted is False
    assert oversized_report.parse_status == "metadata_only_oversized"
    assert oversized_report.raw_content_persisted is False
    assert oversized_report.parsed_summary_persisted is False
