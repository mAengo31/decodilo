from decodilo.lambda_cloud.runtime_smoke_failure_evidence_policy import (
    build_lambda_runtime_smoke_failure_evidence_policy,
)


def test_runtime_smoke_failure_evidence_policy_scopes_capture_to_declared_artifact():
    policy = build_lambda_runtime_smoke_failure_evidence_policy()

    assert policy.policy_status == "policy_defined"
    assert policy.command_must_write_report_on_failure is True
    assert policy.capture_after_nonzero_exit_allowed is True
    assert policy.predeclared_artifact_path == "/tmp/decodilo-runtime-smoke.json"
    assert policy.no_arbitrary_file_reads is True
    assert policy.no_directory_traversal is True
    assert policy.no_extra_file_transfer_except_predeclared_artifact is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
