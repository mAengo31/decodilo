from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lambda_m054a_helpers import write_m054a_inputs

from decodilo.lambda_cloud.ssh_connectivity_one_shot_arming import (
    build_lambda_ssh_connectivity_one_shot_arming_from_paths,
    is_lambda_ssh_connectivity_one_shot_arming_expired,
)


def test_ssh_connectivity_one_shot_arming_is_preview_only(tmp_path):
    paths = write_m054a_inputs(tmp_path)

    report = build_lambda_ssh_connectivity_one_shot_arming_from_paths(
        execution_plan=paths["execution_plan"],
        static_validation=paths["static_validation"],
        authorization=paths["authorization"],
        expires_minutes=15,
        created_at_utc="2026-06-21T12:00:00+00:00",
    )

    assert report.arming_status == "armed_for_one_shot_m054_ssh_connectivity"
    assert report.one_shot_request_send_permitted is False
    assert report.max_launch_attempts == 1
    assert report.max_ssh_connectivity_attempts == 1
    assert report.no_remote_exec is True
    assert report.no_file_transfer is True
    assert report.no_port_forwarding is True
    assert report.launch_allowed is False


def test_ssh_connectivity_one_shot_arming_expiration_detected(tmp_path):
    paths = write_m054a_inputs(tmp_path)
    report = build_lambda_ssh_connectivity_one_shot_arming_from_paths(
        execution_plan=paths["execution_plan"],
        static_validation=paths["static_validation"],
        authorization=paths["authorization"],
        expires_minutes=15,
        created_at_utc="2026-06-21T12:00:00+00:00",
    )
    now = datetime(2026, 6, 21, 12, 16, tzinfo=timezone.utc) + timedelta(seconds=1)

    assert is_lambda_ssh_connectivity_one_shot_arming_expired(
        report,
        now_utc=now.isoformat(),
    )
