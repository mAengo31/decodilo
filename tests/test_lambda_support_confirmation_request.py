from decodilo.lambda_cloud.support_confirmation_request import (
    build_lambda_support_confirmation_request,
)


def test_support_confirmation_request_contains_required_questions_and_no_secrets():
    report = build_lambda_support_confirmation_request()
    question_ids = {item.question_id for item in report.support_request.questions}

    assert report.required_question_count >= 30
    assert "launch_method" in question_ids
    assert "terminate_path_template" in question_ids
    assert "ambiguous_launch_reconciliation" in question_ids
    assert "safe_lifecycle_shape" in question_ids
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert "LAMBDA_API_KEY" not in report.to_json()

