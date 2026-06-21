from __future__ import annotations

from lambda_m046a_helpers import load_json, write_m046a_inputs


def test_m046a_report_records_capacity_selected_wiring(tmp_path):
    paths = write_m046a_inputs(tmp_path)
    report = load_json(paths["m046a"])

    assert report["report_passed"] is True
    assert report["m029_run_accepts_m046_flags"] is True
    assert report["execution_gate_passed"] is True
    assert report["selected_candidate"] == "gpu_8x_a100_80gb_sxm4"
    assert report["old_path_fallback_blocked"] is True
    assert report["m039_path_fallback_blocked"] is True
    assert report["command_preview_status"] == "ready_for_future_m046_capacity_selected_review"
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
