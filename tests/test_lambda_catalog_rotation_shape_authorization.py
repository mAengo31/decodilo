from lambda_m044_helpers import write_m044_inputs

from decodilo.lambda_cloud.catalog_rotation_shape_authorization import (
    build_lambda_catalog_rotation_shape_authorization_from_paths,
)


def test_catalog_rotation_shape_authorization_complete_future_only(tmp_path):
    paths = write_m044_inputs(tmp_path)
    report = build_lambda_catalog_rotation_shape_authorization_from_paths(
        capacity_history=paths["history"],
        retry_policy=paths["retry"],
        rotation_rank=paths["rotation"],
        cost_review=paths["cost"],
        risk_acceptance=paths["risk"],
        operator_decision=paths["operator"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )

    assert (
        report.authorization_status
        == "authorized_for_future_m045_catalog_rotation_launch_review"
    )
    assert report.launch_authorized_for_next_milestone is True
    assert report.launch_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_catalog_rotation_shape_authorization_declined_not_authorized(tmp_path):
    paths = write_m044_inputs(tmp_path, accept=False, decline_wait=True)
    report = build_lambda_catalog_rotation_shape_authorization_from_paths(
        capacity_history=paths["history"],
        retry_policy=paths["retry"],
        rotation_rank=paths["rotation"],
        cost_review=paths["cost"],
        risk_acceptance=paths["risk"],
        operator_decision=paths["operator"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )

    assert report.authorization_status == "not_authorized"
    assert "catalog_rotation_risk_not_accepted" in report.blockers


def test_catalog_rotation_shape_authorization_blocks_missing_cost_review(tmp_path):
    paths = write_m044_inputs(tmp_path, sample_price=True)
    report = build_lambda_catalog_rotation_shape_authorization_from_paths(
        capacity_history=paths["history"],
        retry_policy=paths["retry"],
        rotation_rank=paths["rotation"],
        cost_review=paths["cost"],
        risk_acceptance=paths["risk"],
        operator_decision=paths["operator"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )

    assert report.authorization_status == "not_authorized"
    assert "catalog_rotation_cost_review_not_passed" in report.blockers
