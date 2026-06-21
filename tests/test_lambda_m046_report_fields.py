from __future__ import annotations

from lambda_m046a_helpers import load_json, run_m046_fake


def test_m046_report_contains_capacity_selected_runtime_fields(tmp_path):
    result = run_m046_fake(tmp_path)

    assert result.returncode == 0
    report = load_json(result.workdir / "report.json")  # type: ignore[attr-defined]
    assert report["capacity_selected_path_used"] is True
    assert report["selected_candidate"] == "gpu_8x_a100_80gb_sxm4"
    assert report["selected_candidate_source"] == "product_catalog"
    assert report["selected_region"] == "us-west-1"
    assert report["selected_ssh_key_hash"].startswith("sha256:")
    assert report["strand_payload_compatible"] is True
    assert report["launch_timeout_seconds_effective"] == 30.0
    assert report["response_capture_active"] is True
    assert report["no_auto_launch_retry"] is True
    assert report["old_path_fallback_blocked"] is True
    assert report["m039_path_fallback_blocked"] is True
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
