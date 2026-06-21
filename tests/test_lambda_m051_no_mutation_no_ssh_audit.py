from __future__ import annotations

from lambda_m051_helpers import RAW_TEST_SSH_KEY_NAME, write_m051_inputs

from decodilo.lambda_cloud.m051_no_mutation_no_ssh_audit import (
    build_lambda_m051_no_mutation_no_ssh_audit_from_paths,
)


def test_m051_no_mutation_no_ssh_audit_passes_for_metadata_only(tmp_path):
    paths = write_m051_inputs(tmp_path)

    audit = build_lambda_m051_no_mutation_no_ssh_audit_from_paths(
        metadata_plan=paths["metadata_plan"],
        execution_gate=paths["execution_gate"],
        scope=paths["scope"],
        access_policy=paths["access"],
        ssh_approval=paths["ssh"],
        command_allowlist=paths["commands"],
        package_install_policy=paths["install"],
        no_training_policy=paths["training"],
        m050_report=paths["m050"],
        ssh_key_selection=paths["ssh_key_selection"],
        public_artifacts=[paths["metadata_plan"], paths["execution_gate"], paths["m050"]],
    )

    assert audit.audit_passed is True
    assert audit.ssh_execution_path_allowed is False
    assert audit.remote_command_execution_path_allowed is False
    assert audit.package_install_path_allowed is False
    assert audit.training_path_allowed is False
    assert audit.raw_ssh_key_name_in_public_reports is False
    assert audit.launch_ready is False
    assert audit.launch_allowed is False


def test_m051_no_mutation_no_ssh_audit_blocks_raw_key_leak(tmp_path):
    paths = write_m051_inputs(tmp_path)
    public = tmp_path / "public-report.json"
    public.write_text(f'{{"ssh_key": "{RAW_TEST_SSH_KEY_NAME}"}}\n', encoding="utf-8")

    audit = build_lambda_m051_no_mutation_no_ssh_audit_from_paths(
        metadata_plan=paths["metadata_plan"],
        execution_gate=paths["execution_gate"],
        scope=paths["scope"],
        access_policy=paths["access"],
        ssh_approval=paths["ssh"],
        command_allowlist=paths["commands"],
        package_install_policy=paths["install"],
        no_training_policy=paths["training"],
        m050_report=paths["m050"],
        ssh_key_selection=paths["ssh_key_selection"],
        public_artifacts=[public],
    )

    assert audit.audit_passed is False
    assert audit.raw_ssh_key_name_in_public_reports is True
    assert "raw_ssh_key_name_found_in_public_report" in audit.blockers
