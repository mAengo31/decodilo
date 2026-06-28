from __future__ import annotations

from decodilo.dev.runtime_smoke import load_runtime_smoke_report, run_runtime_smoke


def test_runtime_smoke_report_passes_with_synthetic_one_step(tmp_path):
    out = tmp_path / "runtime-smoke.json"

    report = run_runtime_smoke(synthetic=True, max_steps=1, out=out)
    loaded = load_runtime_smoke_report(out)

    assert report.runtime_smoke_status == "passed"
    assert loaded.runtime_smoke_status == "passed"
    assert loaded.synthetic is True
    assert loaded.max_steps == 1
    assert loaded.network_used is False
    assert loaded.package_install_attempted is False
    assert loaded.download_attempted is False
    assert loaded.training_attempted is False
    assert loaded.torch_required is False
    assert loaded.gpu_required is False
    assert loaded.background_process_started is False
    assert loaded.protocol_or_event_check_passed is True
    assert loaded.replay_or_metric_check_passed is True
    assert loaded.artifact_or_report_check_passed is True
    assert loaded.runtime_checks["update_stream_pre_commit_wait_pending"] is True
    assert loaded.runtime_checks["update_stream_ready_after_commit"] is True
    assert loaded.runtime_checks["update_stream_immediate_ready_after_commit"] is True
    assert loaded.runtime_checks["global_update_acks"] == 1
    assert loaded.runtime_checks["event_log_event_count"] == 1
    assert loaded.artifact_bytes == out.stat().st_size
    assert loaded.artifact_bytes < 8192
    assert loaded.launch_ready is False
    assert loaded.launch_allowed is False


def test_runtime_smoke_report_fails_cleanly_for_invalid_steps(tmp_path):
    out = tmp_path / "runtime-smoke-failed.json"

    report = run_runtime_smoke(synthetic=True, max_steps=2, out=out)

    assert report.runtime_smoke_status == "failed"
    assert out.exists()
    assert "runtime smoke currently requires --max-steps 1" in report.errors
    assert report.failed_check == "argument_validation"
    assert report.error_classification == "invalid_arguments"
    assert report.safe_error_message == "runtime smoke currently requires --max-steps 1"
    assert report.network_used is False
    assert report.package_install_attempted is False
    assert report.download_attempted is False
    assert report.training_attempted is False
    assert report.torch_required is False
    assert report.gpu_required is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
