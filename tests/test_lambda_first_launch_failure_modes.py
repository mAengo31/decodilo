from decodilo.lambda_cloud.first_launch_failure_modes import (
    build_lambda_first_launch_failure_mode_table,
)


def test_first_launch_failure_mode_table_contains_required_modes() -> None:
    table = build_lambda_first_launch_failure_mode_table()
    mode_ids = {mode.mode_id for mode in table.failure_modes}

    assert "duplicate_launch_request" in mode_ids
    assert "launch_timeout_instance_exists" in mode_ids
    assert "terminate_timeout" in mode_ids
    assert table.launch_allowed is False


def test_first_launch_failure_mode_table_serializes() -> None:
    text = build_lambda_first_launch_failure_mode_table().to_json()

    assert "local_process_crash_after_launch" in text
    assert '"billable_action_performed": false' in text
