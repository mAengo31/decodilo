from lambda_m029_helpers import m029_fixture
from lambda_m034a_helpers import write_m034a_artifacts

from decodilo.lambda_cloud.endpoint_spec_operator_confirmation import (
    load_lambda_endpoint_spec_operator_confirmation,
    write_lambda_endpoint_spec_operator_confirmation,
)
from decodilo.lambda_cloud.m034_gate_check import build_lambda_m034_gate_check_from_paths


def test_m034_accepts_medium_confidence_operator_confirmation(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(tmp_path, m029_authorization=fx["authorization"])

    report = build_lambda_m034_gate_check_from_paths(
        m028_report=fx["m028_report"],
        m029_authorization=fx["m029_authorization"],
        endpoint_confirmation=paths["endpoint_confirmation"],
        response_capture_lock=paths["response_capture_lock"],
        timeout_policy=paths["timeout_policy"],
        risk_review=paths["risk_review"],
        correlation_plan=paths["correlation_plan"],
        reconciliation_plan=paths["reconciliation_plan"],
        m034_authorization=paths["m034_authorization"],
        third_go_no_go=paths["third_go_no_go"],
        m033_report=paths["m033_report"],
    )

    assert report.gate_passed is True
    assert report.endpoint_confirmation_status == "confirmed_medium_confidence_accepted"


def test_m034_blocks_rejected_endpoint_confirmation(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(
        tmp_path,
        m029_authorization=fx["authorization"],
        endpoint_accept_medium=False,
    )

    report = build_lambda_m034_gate_check_from_paths(
        m028_report=fx["m028_report"],
        m029_authorization=fx["m029_authorization"],
        endpoint_confirmation=paths["endpoint_confirmation"],
        response_capture_lock=paths["response_capture_lock"],
        timeout_policy=paths["timeout_policy"],
        risk_review=paths["risk_review"],
        correlation_plan=paths["correlation_plan"],
        reconciliation_plan=paths["reconciliation_plan"],
        m034_authorization=paths["m034_authorization"],
        third_go_no_go=paths["third_go_no_go"],
        m033_report=paths["m033_report"],
    )

    assert report.gate_passed is False
    assert "endpoint_confirmation_failed" in report.blockers


def test_m034_blocks_mismatched_launch_endpoint_path(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(tmp_path, m029_authorization=fx["authorization"])
    endpoint = load_lambda_endpoint_spec_operator_confirmation(
        paths["endpoint_confirmation"]
    )
    changed = endpoint.model_copy(
        update={
            "confirmation": endpoint.confirmation.model_copy(
                update={"launch_path_template": "/wrong-launch-path"}
            )
        }
    )
    write_lambda_endpoint_spec_operator_confirmation(paths["endpoint_confirmation"], changed)

    report = build_lambda_m034_gate_check_from_paths(
        m028_report=fx["m028_report"],
        m029_authorization=fx["m029_authorization"],
        endpoint_confirmation=paths["endpoint_confirmation"],
        response_capture_lock=paths["response_capture_lock"],
        timeout_policy=paths["timeout_policy"],
        risk_review=paths["risk_review"],
        correlation_plan=paths["correlation_plan"],
        reconciliation_plan=paths["reconciliation_plan"],
        m034_authorization=paths["m034_authorization"],
        third_go_no_go=paths["third_go_no_go"],
        m033_report=paths["m033_report"],
    )

    assert report.gate_passed is False
    assert "launch_endpoint_path_mismatch" in report.blockers
