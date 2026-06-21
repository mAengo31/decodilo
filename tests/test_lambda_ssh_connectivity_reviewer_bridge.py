from __future__ import annotations

from lambda_m054a_helpers import write_m054a_inputs

from decodilo.lambda_cloud.ssh_connectivity_reviewer_bridge import (
    build_lambda_ssh_connectivity_reviewer_bridge_from_paths,
)


def test_ssh_connectivity_reviewer_bridge_ready_for_safe_package(tmp_path):
    paths = write_m054a_inputs(tmp_path)

    report = build_lambda_ssh_connectivity_reviewer_bridge_from_paths(
        arming=paths["one_shot_arming"],
        static_validation=paths["static_validation"],
        safe_client_command=paths["safe_command"],
    )

    assert report.bridge_status == "reviewer_compatible_one_shot_ready"
    assert report.one_shot_request_send_permitted is True
    assert report.one_shot_ssh_connectivity_probe_permitted is True
    assert report.max_launch_attempts == 1
    assert report.no_remote_exec is True
    assert report.no_file_transfer is True
    assert report.no_port_forwarding is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_connectivity_reviewer_bridge_blocks_expired_arming(tmp_path):
    paths = write_m054a_inputs(tmp_path)

    report = build_lambda_ssh_connectivity_reviewer_bridge_from_paths(
        arming=paths["one_shot_arming"],
        static_validation=paths["static_validation"],
        safe_client_command=paths["safe_command"],
        now_utc="2999-01-01T00:00:00+00:00",
    )

    assert report.bridge_status == "not_ready"
    assert report.one_shot_request_send_permitted is False
    assert "m054_ssh_one_shot_arming_expired" in report.blockers
