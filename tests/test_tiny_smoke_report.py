from __future__ import annotations

from decodilo.dev.tiny_smoke import load_tiny_smoke_report, run_tiny_smoke


def test_tiny_smoke_report_passes_with_synthetic_one_step(tmp_path):
    out = tmp_path / "tiny-smoke.json"

    report = run_tiny_smoke(synthetic=True, max_steps=1, out=out)
    loaded = load_tiny_smoke_report(out)

    assert report.smoke_status == "passed"
    assert loaded.smoke_status == "passed"
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
    assert loaded.artifact_bytes == out.stat().st_size
    assert loaded.artifact_bytes < 8192
    assert loaded.launch_ready is False
    assert loaded.launch_allowed is False


def test_tiny_smoke_report_fails_cleanly_for_invalid_steps(tmp_path):
    out = tmp_path / "tiny-smoke-failed.json"

    report = run_tiny_smoke(synthetic=True, max_steps=2, out=out)

    assert report.smoke_status == "failed"
    assert out.exists()
    assert "tiny smoke currently requires --max-steps 1" in report.errors
    assert report.network_used is False
    assert report.training_attempted is False
