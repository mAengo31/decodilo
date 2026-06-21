from lambda_m036_helpers import endpoint_behavior

from decodilo.lambda_cloud.response_shape_evidence import (
    build_lambda_response_shape_evidence,
)


def test_response_shape_evidence_requires_instance_id_or_async_semantics():
    report = build_lambda_response_shape_evidence(endpoint_behavior())

    assert report.launch_response_instance_id_field == "data.instance_id"
    assert report.terminate_terminal_states == ["terminated", "absent"]
    assert report.launch_ready is False
    assert report.launch_allowed is False

