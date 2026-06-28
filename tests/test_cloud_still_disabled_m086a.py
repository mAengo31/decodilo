from __future__ import annotations

from decodilo.lambda_cloud.m086a_report import LambdaM086AReport
from decodilo.lambda_cloud.m087r_parameter_fragment_authorization import (
    LambdaM087RParameterFragmentAuthorization,
)


def test_m086a_future_authorization_cannot_enable_launch():
    authorization = LambdaM087RParameterFragmentAuthorization(
        authorization_status="authorized_for_future_m087r_parameter_fragment_smoke",
        expected_parameter_fragment_semantics="synthetic_vector_fragments",
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m086a_report_cannot_enable_launch():
    report = LambdaM086AReport(
        report_passed=True,
        parameter_fragment_smoke_command_added=True,
        discovery_status="found_safe_parameter_fragment_command",
        selected_command=[
            "env",
            "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "parameter-fragment-smoke",
            "--synthetic",
            "--fragments",
            "2",
            "--max-steps",
            "1",
            "--out",
            "/tmp/decodilo-parameter-fragment-smoke.json",
        ],
        policy_status="policy_passed",
        m087r_authorization_status=(
            "authorized_for_future_m087r_parameter_fragment_smoke"
        ),
        runbook_preview_status="ready_for_future_m087r_parameter_fragment_review",
        fragment_semantics_status="synthetic_vector_fragments",
        fragments=2,
        max_steps=1,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
