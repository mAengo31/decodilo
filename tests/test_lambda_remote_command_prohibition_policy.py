from __future__ import annotations

import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.remote_command_prohibition_policy import (
    LambdaRemoteCommandProhibitionPolicy,
    build_lambda_remote_command_prohibition_policy,
    remote_command_blockers_for,
)


def test_remote_command_prohibition_denies_shell_and_commands():
    report = build_lambda_remote_command_prohibition_policy()

    assert report.remote_exec_allowed is False
    assert report.interactive_shell_allowed is False
    assert report.command_allowlist_must_be_empty is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_remote_command_prohibition_detects_forbidden_command_strings():
    blockers = remote_command_blockers_for("nvidia-smi && python train.py")

    assert "remote_command_string_present" in blockers
    assert "forbidden_remote_command_token:nvidia-smi" in blockers
    assert "forbidden_remote_command_token:python" in blockers


def test_remote_command_prohibition_rejects_allowed_command_state():
    with pytest.raises(ValidationError):
        LambdaRemoteCommandProhibitionPolicy(remote_exec_allowed=True)
