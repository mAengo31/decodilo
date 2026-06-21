from __future__ import annotations

from lambda_m046a_helpers import load_json, run_m046_fake


def test_m046_capacity_selected_flags_prevent_old_m029_fallback(tmp_path):
    result = run_m046_fake(tmp_path, include_legacy_args=True)

    assert result.returncode == 0
    report = load_json(result.workdir / "report.json")  # type: ignore[attr-defined]
    assert report["capacity_selected_path_used"] is True
    assert report["lower_cost_path_used"] is False
    assert report["old_path_fallback_blocked"] is True
    assert report["selected_candidate"] == "gpu_8x_a100_80gb_sxm4"
    assert report["selected_shape"] == "gpu_8x_a100_80gb_sxm4"
