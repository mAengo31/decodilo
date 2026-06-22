import json

from decodilo.lambda_cloud.ssh_probe_diagnostic_artifact import (
    LambdaSSHProbeDiagnosticArtifact,
)
from decodilo.lambda_cloud.ssh_probe_retry_policy import (
    build_lambda_ssh_probe_retry_policy_from_path,
)


def _write(path, report):
    path.write_text(json.dumps(report.model_dump(mode="json")), encoding="utf-8")


def test_retry_policy_blocks_unknown_exit_255_until_stderr_capture(tmp_path):
    path = tmp_path / "probe.json"
    _write(
        path,
        LambdaSSHProbeDiagnosticArtifact(
            stderr_capture_present=False,
            classification="unknown_exit_255",
            likely_next_action="enable_redacted_stderr_capture",
        ),
    )

    report = build_lambda_ssh_probe_retry_policy_from_path(path)

    assert report.retry_policy_status == "retry_blocked_pending_diagnostics"
    assert "unknown_exit_255_requires_redacted_stderr_capture" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_retry_policy_blocks_permission_denied_until_review(tmp_path):
    path = tmp_path / "probe.json"
    _write(
        path,
        LambdaSSHProbeDiagnosticArtifact(
            stderr_capture_present=True,
            classification="permission_denied_publickey",
            likely_next_action="review_classified_ssh_failure",
        ),
    )

    report = build_lambda_ssh_probe_retry_policy_from_path(path)

    assert report.retry_policy_status == "retry_blocked_pending_diagnostics"
    assert "permission_denied_requires_username_identity_key_attachment_review" in (
        report.blockers
    )
