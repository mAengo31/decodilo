import json

from lambda_m041_helpers import write_m041_inputs

from decodilo.lambda_cloud.catalog_availability_gate_check import (
    build_lambda_catalog_availability_gate_check_from_paths,
)


def test_accepted_risk_catalog_gate_passes_for_future_review(tmp_path):
    paths = write_m041_inputs(tmp_path)

    report = build_lambda_catalog_availability_gate_check_from_paths(
        m042_authorization=paths["m042"],
        availability_plan=paths["plan"],
        risk_acceptance=paths["risk"],
        response_loss_controls=paths["controls"],
        ssh_key_selection=paths["ssh"],
    )

    assert report.gate_passed is True
    assert report.selected_candidate == "gpu_1x_h100_pcie"
    assert report.candidate_source == "product_catalog"
    assert report.live_availability_status == "endpoint_inconclusive"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_declined_risk_catalog_gate_blocks(tmp_path):
    paths = write_m041_inputs(tmp_path, accepted=False)

    report = build_lambda_catalog_availability_gate_check_from_paths(
        m042_authorization=paths["m042"],
        availability_plan=paths["plan"],
        risk_acceptance=paths["risk"],
        response_loss_controls=paths["controls"],
        ssh_key_selection=paths["ssh"],
    )

    assert report.gate_passed is False
    assert "catalog_availability_risk_not_accepted" in report.blockers


def test_missing_ssh_key_blocks_catalog_gate(tmp_path):
    paths = write_m041_inputs(tmp_path)
    data = json.loads(paths["ssh"].read_text(encoding="utf-8"))
    data["selection_passed"] = False
    data["selected_ssh_key_name_redacted_or_hash"] = None
    data["errors"] = ["no existing SSH key names discovered or selected"]
    paths["ssh"].write_text(json.dumps(data), encoding="utf-8")

    report = build_lambda_catalog_availability_gate_check_from_paths(
        m042_authorization=paths["m042"],
        availability_plan=paths["plan"],
        risk_acceptance=paths["risk"],
        response_loss_controls=paths["controls"],
        ssh_key_selection=paths["ssh"],
    )

    assert report.gate_passed is False
    assert "selected_ssh_key_hash_missing" in report.blockers
