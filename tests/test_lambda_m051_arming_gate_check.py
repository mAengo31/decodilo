from __future__ import annotations

from lambda_m051_helpers import write_m051_inputs

from decodilo.lambda_cloud.m051_arming_gate_check import (
    build_lambda_m051_arming_gate_check_from_paths,
)
from decodilo.lambda_cloud.m051_execution_reviewer_bridge import (
    LambdaM051ExecutionReviewerBridge,
    write_lambda_m051_execution_reviewer_bridge,
)


def test_m051_arming_gate_passes_ready_bridge(tmp_path):
    paths = write_m051_inputs(tmp_path)

    gate = build_lambda_m051_arming_gate_check_from_paths(
        reviewer_bridge=paths["reviewer_bridge_m051"],
    )

    assert gate.arming_gate_passed is True
    assert gate.one_shot_request_send_permitted is False
    assert gate.reviewer_bridge_one_shot_request_send_permitted is True
    assert gate.max_launch_attempts == 1
    assert gate.standing_launch_ready is False
    assert gate.standing_launch_allowed is False
    assert gate.launch_ready is False
    assert gate.launch_allowed is False


def test_m051_arming_gate_blocks_not_ready_bridge(tmp_path):
    bridge_path = tmp_path / "bridge.json"
    write_lambda_m051_execution_reviewer_bridge(
        bridge_path,
        LambdaM051ExecutionReviewerBridge(
            bridge_status="not_ready",
            one_shot_request_send_permitted=False,
            blockers=["missing_arming"],
        ),
    )

    gate = build_lambda_m051_arming_gate_check_from_paths(reviewer_bridge=bridge_path)

    assert gate.arming_gate_passed is False
    assert "reviewer_bridge_not_ready" in gate.blockers
