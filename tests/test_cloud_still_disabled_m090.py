from __future__ import annotations

import pytest

from decodilo.lambda_cloud.m090_report import LambdaM090Report
from decodilo.lambda_cloud.post_m089_next_step_decision import (
    LambdaPostM089NextStepDecision,
)


def test_m090_next_step_decision_cannot_enable_launch():
    with pytest.raises(ValueError, match="must not authorize launch"):
        LambdaPostM089NextStepDecision(
            decision_status="next_step_decided",
            recommended_path="pause_and_analyze_bounded_experiment",
            rationale="offline",
            no_automatic_live_authorization=True,
            launch_ready=True,
        )


def test_m090_report_cannot_enable_launch_or_spend():
    with pytest.raises(ValueError, match="must not authorize launch or spend"):
        LambdaM090Report(
            report_passed=True,
            bounded_success_status="remote_bounded_synthetic_diloco_experiment_success",
            bounded_closeout_status="closed_with_warnings",
            bounded_closeout_succeeded=True,
            reconciliation_passed=True,
            bounded_artifact_audit_passed=True,
            scaffold_final_status="complete",
            bounded_experiment_completed=True,
            scientific_gap_assessment_status="scientific_gaps_assessed",
            recommended_next_path="pause_and_analyze_bounded_experiment",
            no_new_live_authorization=True,
            historical_billable_action_performed=True,
            billable_action_performed=True,
        )
