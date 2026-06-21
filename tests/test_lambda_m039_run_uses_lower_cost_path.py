from __future__ import annotations

from lambda_m039a_helpers import load_json, run_m039_fake


def test_m039_run_uses_lower_cost_path_without_legacy_artifacts(tmp_path):
    result = run_m039_fake(tmp_path)

    assert result.returncode == 0
    report = load_json(result.workdir / "report.json")  # type: ignore[attr-defined]
    assert report["lower_cost_path_used"] is True
    assert report["selected_shape"] == "gpu_1x_h100_pcie"
    assert report["selected_region"] == "us-west-1"
    assert report["strand_payload_compatible"] is True
    assert report["real_lambda_api_used"] is False
