from lambda_m041_helpers import write_m041_inputs

from decodilo.lambda_cloud.catalog_availability_m042_authorization import (
    build_lambda_catalog_availability_m042_authorization_from_paths,
)


def test_complete_accepted_risk_authorizes_future_m042_review(tmp_path):
    paths = write_m041_inputs(tmp_path)
    report = build_lambda_catalog_availability_m042_authorization_from_paths(
        capacity_closeout=paths["closeout"],
        availability_authorization=paths["authorization"],
        go_no_go=paths["go"],
        risk_acceptance=paths["risk"],
        operator_decision=paths["decision"],
        response_loss_controls=paths["controls"],
    )

    assert (
        report.authorization_status
        == "authorized_for_future_m042_catalog_availability_launch_review"
    )
    assert report.selected_candidate == "gpu_1x_h100_pcie"
    assert report.candidate_source == "product_catalog"
    assert report.launch_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_declined_risk_does_not_authorize_m042(tmp_path):
    paths = write_m041_inputs(tmp_path, accepted=False)
    report = build_lambda_catalog_availability_m042_authorization_from_paths(
        capacity_closeout=paths["closeout"],
        availability_authorization=paths["authorization"],
        go_no_go=paths["go"],
        risk_acceptance=paths["risk"],
        operator_decision=paths["decision"],
        response_loss_controls=paths["controls"],
    )

    assert report.authorization_status == "not_authorized"
    assert "catalog_availability_risk_not_accepted" in report.blockers


def test_missing_response_loss_controls_blocks_m042_authorization(tmp_path):
    paths = write_m041_inputs(tmp_path)
    data = paths["controls"].read_text(encoding="utf-8")
    paths["controls"].write_text(
        data.replace('"controls_passed": true', '"controls_passed": false').replace(
            '"blockers": []',
            '"blockers": ["response_loss_controls_failed"]',
            1,
        ),
        encoding="utf-8",
    )

    report = build_lambda_catalog_availability_m042_authorization_from_paths(
        capacity_closeout=paths["closeout"],
        availability_authorization=paths["authorization"],
        go_no_go=paths["go"],
        risk_acceptance=paths["risk"],
        operator_decision=paths["decision"],
        response_loss_controls=paths["controls"],
    )

    assert report.authorization_status == "not_authorized"
    assert "response_loss_controls_failed" in report.blockers
