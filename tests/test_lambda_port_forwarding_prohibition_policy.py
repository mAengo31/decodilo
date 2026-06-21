from __future__ import annotations

import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.port_forwarding_prohibition_policy import (
    LambdaPortForwardingProhibitionPolicy,
    build_lambda_port_forwarding_prohibition_policy,
)


def test_port_forwarding_prohibition_denies_all_forwarding():
    report = build_lambda_port_forwarding_prohibition_policy()

    assert report.local_forward_allowed is False
    assert report.remote_forward_allowed is False
    assert report.dynamic_forward_allowed is False
    assert report.agent_forward_allowed is False
    assert report.x11_forward_allowed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_port_forwarding_prohibition_rejects_local_forward():
    with pytest.raises(ValidationError):
        LambdaPortForwardingProhibitionPolicy(local_forward_allowed=True)
