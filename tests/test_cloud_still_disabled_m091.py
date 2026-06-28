from __future__ import annotations

import pytest

from decodilo.lambda_cloud.m091_report import LambdaM091Report
from decodilo.lambda_cloud.post_m090_next_branch_decision import (
    LambdaPostM090NextBranchDecision,
)


def test_m091_next_branch_decision_cannot_enable_launch():
    with pytest.raises(ValueError, match="must remain offline"):
        LambdaPostM090NextBranchDecision(
            decision_status="next_branch_selected",
            recommended_branch="plan_tiny_real_training_smoke",
            rationale="offline decision only",
            launch_ready=True,
        )


def test_m091_next_branch_decision_cannot_authorize_live_execution():
    with pytest.raises(ValueError, match="cannot authorize live execution"):
        LambdaPostM090NextBranchDecision(
            decision_status="next_branch_selected",
            recommended_branch="plan_tiny_real_training_smoke",
            rationale="offline decision only",
            no_live_authorization=False,
        )


def test_m091_report_cannot_enable_launch_or_spend():
    with pytest.raises(ValueError, match="must remain offline"):
        LambdaM091Report(
            report_passed=True,
            scaffold_completion_status="complete",
            bounded_experiment_interpretation_status="evidence_interpreted",
            recommended_next_branch="plan_tiny_real_training_smoke",
            another_scaffold_run_justified=False,
            no_live_authorization=True,
            historical_billable_action_performed=True,
            billable_action_performed=True,
        )
