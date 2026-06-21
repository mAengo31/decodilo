from __future__ import annotations

from lambda_m054a_helpers import write_m054a_inputs

from decodilo.lambda_cloud.ssh_connectivity_execution_plan import (
    build_lambda_ssh_connectivity_execution_plan_from_path,
)


def test_ssh_connectivity_execution_plan_forbids_remote_work(tmp_path):
    paths = write_m054a_inputs(tmp_path)

    report = build_lambda_ssh_connectivity_execution_plan_from_path(
        paths["authorization"],
    )

    assert report.plan_status == "plan_defined"
    assert report.max_instances == 1
    assert report.remote_exec_allowed is False
    assert report.interactive_shell_allowed is False
    assert report.file_transfer_allowed is False
    assert report.port_forwarding_allowed is False
    assert report.package_install_allowed is False
    assert report.training_allowed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
