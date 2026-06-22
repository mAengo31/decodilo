import json

from decodilo.lambda_cloud.m055b_report import build_lambda_m055b_report_from_paths
from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    build_lambda_ssh_stderr_capture_policy,
    write_lambda_ssh_stderr_capture_policy,
)
from decodilo.lambda_cloud.ssh_host_key_policy import (
    build_lambda_ssh_host_key_policy,
    write_lambda_ssh_host_key_policy,
)
from decodilo.lambda_cloud.ssh_identity_policy import (
    build_lambda_ssh_identity_policy,
    write_lambda_ssh_identity_policy,
)
from decodilo.lambda_cloud.ssh_private_key_file_policy import (
    build_lambda_ssh_private_key_file_policy,
    write_lambda_ssh_private_key_file_policy,
)
from decodilo.lambda_cloud.ssh_probe_diagnostic_artifact import (
    LambdaSSHProbeDiagnosticArtifact,
    write_lambda_ssh_probe_diagnostic,
)
from decodilo.lambda_cloud.ssh_probe_retry_policy import (
    build_lambda_ssh_probe_retry_policy_from_path,
    write_lambda_ssh_probe_retry_policy,
)
from decodilo.lambda_cloud.ssh_provider_key_attachment_diagnostic import (
    build_lambda_ssh_provider_key_attachment_diagnostic_from_paths,
    write_lambda_ssh_provider_key_attachment_diagnostic,
)
from decodilo.lambda_cloud.ssh_username_policy import (
    build_lambda_ssh_username_policy,
    write_lambda_ssh_username_policy,
)


def test_m055b_report_rolls_up_offline_diagnostics(tmp_path):
    username = tmp_path / "username.json"
    host_key = tmp_path / "host-key.json"
    identity = tmp_path / "identity.json"
    private_key = tmp_path / "private-key.json"
    stderr = tmp_path / "stderr.json"
    provider = tmp_path / "provider.json"
    probe = tmp_path / "probe.json"
    retry = tmp_path / "retry.json"
    selection = tmp_path / "selection.json"
    selection.write_text(
        json.dumps({"selected_ssh_key_name_redacted_or_hash": "sha256:key"}),
        encoding="utf-8",
    )
    write_lambda_ssh_username_policy(username, build_lambda_ssh_username_policy())
    write_lambda_ssh_host_key_policy(host_key, build_lambda_ssh_host_key_policy())
    write_lambda_ssh_identity_policy(identity, build_lambda_ssh_identity_policy())
    write_lambda_ssh_private_key_file_policy(
        private_key,
        build_lambda_ssh_private_key_file_policy(),
    )
    write_lambda_ssh_stderr_capture_policy(stderr, build_lambda_ssh_stderr_capture_policy())
    write_lambda_ssh_provider_key_attachment_diagnostic(
        provider,
        build_lambda_ssh_provider_key_attachment_diagnostic_from_paths(
            ssh_key_selection=selection,
            local_private_key_matches_public_identity=True,
        ),
    )
    write_lambda_ssh_probe_diagnostic(
        probe,
        LambdaSSHProbeDiagnosticArtifact(
            stderr_capture_present=True,
            classification="auth_failed_unknown",
            likely_next_action="review_classified_ssh_failure",
        ),
    )
    write_lambda_ssh_probe_retry_policy(
        retry,
        build_lambda_ssh_probe_retry_policy_from_path(probe),
    )

    report = build_lambda_m055b_report_from_paths(
        username_policy=username,
        host_key_policy=host_key,
        identity_policy=identity,
        private_key_file_policy=private_key,
        stderr_policy=stderr,
        provider_key_diagnostic=provider,
        probe_diagnostic=probe,
        retry_policy=retry,
    )

    assert report.report_passed is True
    assert report.selected_username == "ubuntu"
    assert report.launch_ready is False
    assert report.launch_allowed is False
