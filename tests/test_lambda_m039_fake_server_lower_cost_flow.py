from __future__ import annotations

from lambda_m039a_helpers import load_json, run_m039_fake


def test_m039_fake_server_lower_cost_launch_and_terminate_flow(tmp_path):
    result = run_m039_fake(tmp_path)

    assert result.returncode == 0
    report = load_json(result.workdir / "report.json")  # type: ignore[attr-defined]
    diagnostics = load_json(result.workdir / "transport-diagnostics.json")  # type: ignore[attr-defined]
    assert report["launch_request_sent"] is True
    assert report["launch_response_received"] is True
    assert report["termination_request_sent"] is True
    assert report["termination_verified"] is True
    assert report["manual_review_required"] is False
    assert report["mutating_operations"] == 2
    assert report["billable_action_performed"] is False
    assert report["no_auto_launch_retry"] is True
    assert diagnostics["status_captured_before_parse"] is True
    launch_diagnostics = [
        d for d in diagnostics["diagnostics"] if d["operation"] == "launch_one_instance"
    ]
    assert len(launch_diagnostics) == 1
