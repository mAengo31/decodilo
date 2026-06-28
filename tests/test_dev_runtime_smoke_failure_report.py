from __future__ import annotations

import json

from decodilo.dev import runtime_smoke


def test_runtime_smoke_forced_update_stream_failure_writes_bounded_report(
    tmp_path,
    monkeypatch,
):
    out = tmp_path / "runtime-smoke-failed.json"

    def fail_update_stream() -> dict[str, bool | int | float | str]:
        raise TimeoutError

    monkeypatch.setattr(runtime_smoke, "_run_update_stream_check", fail_update_stream)

    report = runtime_smoke.run_runtime_smoke(synthetic=True, max_steps=1, out=out)
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert report.runtime_smoke_status == "failed"
    assert payload["runtime_smoke_status"] == "failed"
    assert payload["failed_check"] == "protocol_or_event_check"
    assert payload["error_classification"] == "update_stream_check_failed"
    assert payload["safe_error_message"] == "update_stream_check_failed:TimeoutError"
    assert payload["network_used"] is False
    assert payload["package_install_attempted"] is False
    assert payload["download_attempted"] is False
    assert payload["training_attempted"] is False
    assert payload["torch_required"] is False
    assert payload["gpu_required"] is False
    assert payload["launch_ready"] is False
    assert payload["launch_allowed"] is False
    assert out.stat().st_size < 8192
