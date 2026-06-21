from __future__ import annotations

from lambda_m039a_helpers import load_json, run_m039_fake


def test_m039_report_contains_lower_cost_runtime_fields(tmp_path):
    result = run_m039_fake(tmp_path)

    assert result.returncode == 0
    report = load_json(result.workdir / "report.json")  # type: ignore[attr-defined]
    assert report["lower_cost_path_used"] is True
    assert report["selected_shape"] == "gpu_1x_h100_pcie"
    assert report["selected_region"] == "us-west-1"
    assert report["selected_ssh_key_hash"].startswith("sha256:")
    assert report["strand_payload_compatible"] is True
    assert report["launch_timeout_seconds_effective"] == 30.0
    assert report["response_capture_active"] is True
    assert report["no_auto_launch_retry"] is True
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
