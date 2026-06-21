from lambda_m036_helpers import endpoint_behavior, support_response, validation


def test_endpoint_behavior_builds_from_validated_support_response():
    report = endpoint_behavior()

    assert report.launch_method == "POST"
    assert report.launch_path_template == "/instance-operations/launch"
    assert report.terminate_method == "POST"
    assert report.launch_response_instance_id_field == "data.instance_id"
    assert report.terminate_terminal_states == ["terminated", "absent"]
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_missing_instance_id_requires_async_explanation():
    response = support_response(
        missing=("launch_instance_id_field", "launch_async_without_id")
    )
    report = endpoint_behavior(response=response, validation_report=validation(response))

    assert report.launch_async_without_id_possible is False
    assert "missing_instance_id_field_or_async_explanation" in report.blockers
