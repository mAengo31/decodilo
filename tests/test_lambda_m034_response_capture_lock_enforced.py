from lambda_m029_helpers import m029_fixture
from lambda_m034a_helpers import write_m034a_artifacts

from decodilo.lambda_cloud.m034_gate_check import build_lambda_m034_gate_check_from_paths


def test_m034_blocks_missing_status_before_parse(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(
        tmp_path,
        m029_authorization=fx["authorization"],
        capture_http_status_before_parse=False,
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
    assert "capture_http_status_before_parse" in report.blockers


def test_m034_blocks_body_sample_enabled_without_runtime_justification(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(
        tmp_path,
        m029_authorization=fx["authorization"],
        body_sample_enabled=True,
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
    assert "response_body_sample_enabled_without_m034_justification" in report.blockers
