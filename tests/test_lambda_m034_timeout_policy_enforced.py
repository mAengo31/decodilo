from lambda_m029_helpers import m029_fixture
from lambda_m034a_helpers import write_m034a_artifacts

from decodilo.lambda_cloud.m034_gate_check import build_lambda_m034_gate_check_from_paths
from decodilo.lambda_cloud.real_mutation_transport import LambdaM029TransportConfig


def test_m034_blocks_timeout_policy_below_30_seconds(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(
        tmp_path,
        m029_authorization=fx["authorization"],
        launch_timeout_seconds=10.0,
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
    assert "launch_timeout_below_m034_minimum" in report.blockers


def test_m034_blocks_auto_launch_retry_policy(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(
        tmp_path,
        m029_authorization=fx["authorization"],
        no_auto_launch_retry=False,
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
    assert "automatic_launch_retry_allowed" in report.blockers


def test_transport_default_aligns_with_strand_30_seconds():
    config = LambdaM029TransportConfig(
        base_url="memory://lambda-m034-test",
        fake_server_mode=True,
    )

    assert config.timeout_seconds == 30.0
