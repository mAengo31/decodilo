from __future__ import annotations

from decodilo.dev.runtime_smoke import run_runtime_smoke


def test_runtime_smoke_update_stream_path_is_deterministic(tmp_path):
    out = tmp_path / "runtime-smoke.json"

    report = run_runtime_smoke(synthetic=True, max_steps=1, out=out)

    assert report.runtime_smoke_status == "passed"
    assert report.protocol_or_event_check_passed is True
    assert report.runtime_checks["update_stream_pre_commit_wait_pending"] is True
    assert report.runtime_checks["update_stream_ready_after_commit"] is True
    assert report.runtime_checks["update_stream_immediate_ready_after_commit"] is True
    assert report.runtime_checks["global_update_broadcasts"] == 1
    assert report.runtime_checks["global_update_messages_sent"] == 1
    assert report.runtime_checks["global_update_acks"] == 1
    assert report.network_used is False
    assert report.package_install_attempted is False
    assert report.download_attempted is False
    assert report.training_attempted is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
