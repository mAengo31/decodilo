import json

from decodilo.lambda_cloud.ssh_probe_diagnostic_artifact import (
    build_lambda_ssh_probe_diagnostic_from_paths,
)


def test_probe_diagnostic_historical_missing_stderr_unknown_exit_255(tmp_path):
    report_path = tmp_path / "m055-report.json"
    report_path.write_text(
        json.dumps(
            {
                "ssh_auth_result": "auth_failed",
                "ssh_port_reachable": True,
                "host_discovery_status": "FOUND",
            }
        ),
        encoding="utf-8",
    )

    report = build_lambda_ssh_probe_diagnostic_from_paths(fallback_report=report_path)

    assert report.stderr_capture_present is False
    assert report.classification == "unknown_exit_255"
    assert report.tcp_readiness_succeeded is True
    assert report.likely_next_action == "enable_redacted_stderr_capture"
    assert "stderr_capture_missing_for_exit_255" in report.blockers


def test_probe_diagnostic_classifies_future_stderr(tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "ssh-connectivity-evidence.json").write_text(
        json.dumps(
            {
                "exit_status": 255,
                "stderr_redacted": "Permission denied (publickey).",
                "ssh_port_reachable": True,
            }
        ),
        encoding="utf-8",
    )

    report = build_lambda_ssh_probe_diagnostic_from_paths(workdir=workdir)

    assert report.stderr_capture_present is True
    assert report.classification == "permission_denied_publickey"
    assert report.blockers == []
