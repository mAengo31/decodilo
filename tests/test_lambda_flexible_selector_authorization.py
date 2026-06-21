from lambda_m044g_helpers import write_m044g_inputs

from decodilo.lambda_cloud.flexible_selector_authorization import (
    load_lambda_flexible_selector_authorization,
)


def test_flexible_selector_authorization_uses_selector_output(tmp_path):
    paths = write_m044g_inputs(tmp_path)
    report = load_lambda_flexible_selector_authorization(paths["authorization"])

    assert (
        report.authorization_status
        == "authorized_for_future_flexible_selector_launch_review"
    )
    assert report.authorization_source == "flexible_selector_output"
    assert report.fixed_shape_path_used is False
    assert report.launch_authorized_for_next_milestone is True
    assert report.launch_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_flexible_selector_authorization_blocks_without_risk_acceptance(tmp_path):
    paths = write_m044g_inputs(tmp_path, risk_accepted=False)
    report = load_lambda_flexible_selector_authorization(paths["authorization"])

    assert report.authorization_status == "not_authorized"
    assert "selector_launch_selection_not_allowed" in report.blockers
    assert "catalog_only_risk_acceptance_required" in report.blockers


def test_flexible_selector_authorization_requires_ssh_key(tmp_path):
    paths = write_m044g_inputs(tmp_path, missing_ssh=True)
    report = load_lambda_flexible_selector_authorization(paths["authorization"])

    assert report.authorization_status == "not_authorized"
    assert "existing_ssh_key_selection_required" in report.blockers
