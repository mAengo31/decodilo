from __future__ import annotations

from lambda_m039a_helpers import load_json, run_m039_fake


def test_m039_lower_cost_flags_prevent_old_shape_fallback(tmp_path):
    result = run_m039_fake(tmp_path, include_legacy_args=True)

    assert result.returncode == 0
    report = load_json(result.workdir / "report.json")  # type: ignore[attr-defined]
    assert report["lower_cost_path_used"] is True
    assert report["selected_shape"] == "gpu_1x_h100_pcie"
    for artifact in result.workdir.iterdir():  # type: ignore[attr-defined]
        if artifact.is_file():
            assert "gpu_8x_h100_sxm" not in artifact.read_text(encoding="utf-8")
