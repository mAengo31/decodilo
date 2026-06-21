from lambda_m029_helpers import m029_fixture
from lambda_m034a_helpers import write_m034a_artifacts

from decodilo.lambda_cloud.m034_gate_check import build_lambda_m034_gate_check_from_paths
from decodilo.lambda_cloud.third_attempt_reconciliation_plan import (
    load_lambda_third_attempt_reconciliation_plan,
    write_lambda_third_attempt_reconciliation_plan,
)


def test_m034_reconciliation_allows_exact_candidate_policy(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(
        tmp_path,
        m029_authorization=fx["authorization"],
        candidate_confidence="exact",
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

    assert report.gate_passed is True
    assert report.candidate_confidence == "exact"
    assert report.terminate_allowed is True


def test_m034_blocks_missing_final_termination_verification(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(tmp_path, m029_authorization=fx["authorization"])
    reconciliation = load_lambda_third_attempt_reconciliation_plan(
        paths["reconciliation_plan"]
    )
    write_lambda_third_attempt_reconciliation_plan(
        paths["reconciliation_plan"],
        reconciliation.model_copy(
            update={"final_read_only_termination_verification_required": False}
        ),
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
    assert "final_read_only_termination_verification_required" in report.blockers
