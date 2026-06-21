from lambda_m035_helpers import support_request


def test_support_request_includes_required_questions_and_no_secrets():
    report = support_request()
    questions = {item.question_id for item in report.support_request.questions}

    assert report.support_request_generated is True
    assert "launch_endpoint" in questions
    assert "launch_response" in questions
    assert "idempotency" in questions
    assert "termination_states" in questions
    assert report.support_request.no_secrets_included is True
    assert "Bearer" not in report.to_json()
    assert report.launch_ready is False
    assert report.launch_allowed is False
