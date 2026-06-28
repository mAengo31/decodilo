from __future__ import annotations

import subprocess
from pathlib import Path

from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    M075R_RUNTIME_SMOKE_COMMAND,
    LambdaRemoteVerticalSliceCommandEntry,
    LambdaRemoteVerticalSliceCommandManifest,
    _SSHBannerReadiness,
    render_lambda_remote_vertical_slice_argv,
    run_lambda_remote_vertical_slice_manifest,
)
from decodilo.lambda_cloud.ssh_connectivity_probe import _SSHPortReadiness
from decodilo.lambda_cloud.ssh_host_discovery import LambdaSSHHostDiscoveryResult


def test_remote_vslice_captures_declared_artifact_metadata_after_command_failure(
    monkeypatch,
    tmp_path,
):
    private_key = tmp_path / "id_rsa"
    private_key.write_text("redacted", encoding="utf-8")
    private_key.chmod(0o600)
    manifest = LambdaRemoteVerticalSliceCommandManifest(
        milestone="M075R",
        max_remote_commands=1,
        command_entries=[
            LambdaRemoteVerticalSliceCommandEntry(
                stage="runtime_smoke_command",
                exact_command=render_lambda_remote_vertical_slice_argv(
                    M075R_RUNTIME_SMOKE_COMMAND
                ),
                argv_tokens=list(M075R_RUNTIME_SMOKE_COMMAND),
                timeout_seconds=30,
                failure_stage_if_nonzero="runtime_smoke_command",
            )
        ],
    )

    monkeypatch.setattr(
        "decodilo.lambda_cloud.remote_vertical_slice_policy._wait_for_ssh_port_ready",
        lambda **_: _SSHPortReadiness(
            reachable=True,
            poll_count=1,
            elapsed_seconds=0.01,
        ),
    )
    monkeypatch.setattr(
        "decodilo.lambda_cloud.remote_vertical_slice_policy._wait_for_ssh_banner_ready",
        lambda **_: _SSHBannerReadiness(
            ready=True,
            poll_count=1,
            elapsed_seconds=0.01,
            banner_prefix_observed=True,
        ),
    )

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN202 - subprocess test double.
        del kwargs
        if cmd[0] == "scp":
            local_path = Path(cmd[-1])
            local_path.write_text(
                '{"runtime_smoke_status":"failed","network_used":false}\n',
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 1, "redacted failure report\n", "")

    monkeypatch.setattr(
        "decodilo.lambda_cloud.remote_vertical_slice_policy.subprocess.run",
        fake_run,
    )

    evidence = run_lambda_remote_vertical_slice_manifest(
        owned_instance_id="instance-1234567890",
        instance_payload={"ip": "203.0.113.10"},
        private_key_path=private_key,
        manifest=manifest,
        manifest_hash="a" * 64,
        host_discovery_result=LambdaSSHHostDiscoveryResult(
            status="FOUND",
            host="203.0.113.10",
            host_redacted="<redacted-host>",
            source_path="data[0].ip",
        ),
    )

    assert evidence.failed_stage == "runtime_smoke_command"
    assert evidence.vertical_slice_status == "vertical_slice_failed_at_runtime_smoke_command"
    assert evidence.experiment_output_artifact_capture_attempted is True
    assert evidence.experiment_output_artifact_capture_succeeded is True
    assert evidence.experiment_output_artifact_exists is True
    assert evidence.experiment_output_artifact_bytes is not None
    assert evidence.experiment_output_artifact_sha256 is not None
    assert evidence.experiment_output_artifact_secret_scan_passed is True
    assert evidence.experiment_output_artifact_body_capture_attempted is True
    assert evidence.experiment_output_artifact_body_capture_succeeded is True
    assert evidence.experiment_output_artifact_body_persisted is True
    assert evidence.experiment_output_artifact_body_json == {
        "runtime_smoke_status": "failed",
        "network_used": False,
    }
    assert evidence.experiment_output_artifact_parsed_summary_persisted is True
    assert evidence.experiment_output_artifact_parsed_summary == {
        "runtime_smoke_status": "failed",
        "network_used": False,
    }
