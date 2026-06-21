from __future__ import annotations

from lambda_m051_helpers import load_json, run_m051_fake


def test_m051_fake_server_metadata_bootstrap_launch_and_terminate_flow(tmp_path):
    result = run_m051_fake(tmp_path)

    assert result.returncode == 0, result.stderr
    report = load_json(result.workdir / "report.json")  # type: ignore[attr-defined]
    diagnostics = load_json(result.workdir / "transport-diagnostics.json")  # type: ignore[attr-defined]
    public_report = (result.workdir / "report.json").read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert report["metadata_bootstrap_path_used"] is True
    assert report["metadata_only"] is True
    assert report["selected_shape"] == "gpu_8x_a100_80gb_sxm4"
    assert report["selected_region"] == "us-midwest-1"
    assert report["ssh_attempted"] is False
    assert report["remote_command_attempted"] is False
    assert report["package_install_attempted"] is False
    assert report["training_attempted"] is False
    assert report["launch_request_sent"] is True
    assert report["launch_response_received"] is True
    assert report["termination_request_sent"] is True
    assert report["termination_verified"] is True
    assert report["manual_review_required"] is False
    assert report["billable_action_performed"] is False
    assert report["no_auto_launch_retry"] is True
    assert "existing-key" not in public_report
    assert diagnostics["status_captured_before_parse"] is True


def test_m051_fake_server_requires_all_bootstrap_artifacts(tmp_path):
    result = run_m051_fake(tmp_path, omit={"--m051-metadata-plan"})

    assert result.returncode != 0
    assert "M051 metadata bootstrap run requires all M051 artifacts" in result.stderr
