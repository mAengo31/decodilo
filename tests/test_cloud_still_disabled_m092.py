from __future__ import annotations

import pytest

from decodilo.dev.tiny_real_training_smoke import TinyRealTrainingSmokeReport
from decodilo.lambda_cloud.m092_report import LambdaM092Report
from decodilo.lambda_cloud.m093r_tiny_real_training_authorization import (
    LambdaM093RTinyRealTrainingAuthorization,
)


def test_tiny_real_training_report_cannot_enable_launch():
    with pytest.raises(ValueError, match="cannot enable launch"):
        TinyRealTrainingSmokeReport(
            tiny_real_training_smoke_status="failed",
            synthetic=True,
            model="tiny-linear",
            steps_requested=1,
            steps_completed=0,
            optimizer="adamw",
            training_attempted=False,
            real_training_mechanics_exercised=False,
            elapsed_seconds=0.0,
            launch_allowed=True,
        )


def test_m093r_authorization_cannot_run_now():
    with pytest.raises(ValueError, match="future-only"):
        LambdaM093RTinyRealTrainingAuthorization(
            authorization_status="authorized_for_future_m093r_tiny_real_training_smoke",
            run_now=True,
        )


def test_m092_report_cannot_enable_launch_or_spend():
    with pytest.raises(ValueError, match="must not authorize launch or spend"):
        LambdaM092Report(
            report_passed=True,
            readiness_status="ready_for_future_tiny_real_training_planning",
            discovery_status="found_safe_tiny_real_training_command",
            policy_status="policy_passed",
            m093r_authorization_status=(
                "authorized_for_future_m093r_tiny_real_training_smoke"
            ),
            runbook_preview_status="ready_for_future_m093r_tiny_real_training_review",
            tiny_real_training_command_added=True,
            real_training_mechanics_exercised=True,
            torch_required=False,
            gpu_required=False,
            billable_action_performed=True,
        )
