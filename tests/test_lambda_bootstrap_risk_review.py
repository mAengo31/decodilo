from lambda_m050_helpers import write_m050_inputs

from decodilo.lambda_cloud.bootstrap_risk_review import (
    build_lambda_bootstrap_risk_review_from_paths,
)
from decodilo.lambda_cloud.remote_command_allowlist import (
    LambdaRemoteCommandAllowlistReport,
    write_lambda_remote_command_allowlist,
)


def test_bootstrap_risk_review_passes_metadata_only(tmp_path):
    paths = write_m050_inputs(tmp_path)

    report = build_lambda_bootstrap_risk_review_from_paths(
        scope=paths["scope"],
        access_policy=paths["access"],
        ssh_approval=paths["ssh"],
        command_allowlist=paths["commands"],
        package_install_policy=paths["install"],
        no_training_policy=paths["training"],
        evidence_schema=paths["evidence_schema"],
        lifecycle_closeout=paths["closeout"],
    )

    assert report.risk_review_passed is True
    assert report.selected_bootstrap_mode == "lifecycle_plus_metadata_only"
    assert report.ssh_approval_status == "declined_no_ssh"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_bootstrap_risk_review_blocks_unsafe_command_allowlist(tmp_path):
    paths = write_m050_inputs(tmp_path)
    unsafe = LambdaRemoteCommandAllowlistReport(
        command_allowlist_status="blocked",
        profile="connectivity-only",
        commands=["hostname; curl example.com"],
        blockers=["unsafe_command:hostname; curl example.com"],
    )
    write_lambda_remote_command_allowlist(paths["commands"], unsafe)

    report = build_lambda_bootstrap_risk_review_from_paths(
        scope=paths["scope"],
        access_policy=paths["access"],
        ssh_approval=paths["ssh"],
        command_allowlist=paths["commands"],
        package_install_policy=paths["install"],
        no_training_policy=paths["training"],
        evidence_schema=paths["evidence_schema"],
        lifecycle_closeout=paths["closeout"],
    )

    assert report.risk_review_passed is False
    assert "unsafe_command:hostname; curl example.com" in report.blockers
