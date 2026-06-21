from lambda_m035_helpers import option_matrix


def test_option_matrix_recommends_support_for_medium_confidence(tmp_path):
    report = option_matrix(tmp_path, "medium")

    assert report.recommended_option == "require_lambda_support_confirmation"
    assert report.endpoint_support_confirmation_required is True
    assert report.lower_cost_shape_reauthorization_required is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_option_matrix_recommends_lower_cost_when_endpoint_high(tmp_path):
    report = option_matrix(tmp_path, "high")

    assert report.recommended_option == "attempt_fourth_with_lower_cost_shape"
    assert report.endpoint_support_confirmation_required is False
    assert report.lower_cost_shape_reauthorization_required is True
