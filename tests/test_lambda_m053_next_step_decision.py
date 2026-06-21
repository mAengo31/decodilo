from __future__ import annotations

import pytest
from lambda_m052_helpers import write_m052_inputs
from pydantic import ValidationError

from decodilo.lambda_cloud.m053_next_step_decision import (
    LambdaM053NextStepDecision,
    build_lambda_m053_next_step_decision_from_paths,
)


def test_successful_metadata_closeout_plans_ssh_connectivity_review(tmp_path):
    paths = write_m052_inputs(tmp_path)

    report = build_lambda_m053_next_step_decision_from_paths(
        metadata_closeout=paths["closeout"],
        strategy_update=paths["strategy"],
    )

    assert report.decision_status == "plan_ssh_connectivity_only_review"
    assert report.ssh_authorized_now is False
    assert report.remote_commands_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_forbidden_m053_status_is_rejected():
    with pytest.raises(ValidationError):
        LambdaM053NextStepDecision.model_validate(
            {"decision_status": "ssh_now"},
        )
