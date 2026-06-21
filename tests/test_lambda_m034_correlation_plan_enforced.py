from lambda_m029_helpers import m029_fixture
from lambda_m034a_helpers import write_m034a_artifacts

from decodilo.lambda_cloud.m034_gate_check import build_lambda_m034_gate_check_from_paths
from decodilo.lambda_cloud.third_attempt_correlation_plan import (
    load_lambda_third_attempt_correlation_plan,
    write_lambda_third_attempt_correlation_plan,
)


def test_m034_correlation_plan_must_match_planned_shape(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(tmp_path, m029_authorization=fx["authorization"])
    correlation = load_lambda_third_attempt_correlation_plan(paths["correlation_plan"])
    write_lambda_third_attempt_correlation_plan(
        paths["correlation_plan"],
        correlation.model_copy(update={"planned_shape": "gpu_1x_wrong"}),
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
    assert "third_attempt_planned_shape_mismatch" in report.blockers


def test_m034_correlation_plan_must_forbid_automatic_retry(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(tmp_path, m029_authorization=fx["authorization"])
    correlation = load_lambda_third_attempt_correlation_plan(paths["correlation_plan"])
    write_lambda_third_attempt_correlation_plan(
        paths["correlation_plan"],
        correlation.model_copy(update={"no_automatic_retry": False}),
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
    assert "third_attempt_correlation_allows_retry" in report.blockers
