from __future__ import annotations

from decodilo.lambda_cloud.remote_vslice_candidate_selector import (
    LambdaRemoteVSliceCandidateSelection,
    write_lambda_remote_vslice_candidate_selection,
)
from decodilo.lambda_cloud.remote_vslice_retry_decision import (
    build_lambda_remote_vslice_retry_decision_from_path,
)


def test_retry_decision_waits_without_fresh_discovery(tmp_path):
    selection_path = tmp_path / "selection.json"
    write_lambda_remote_vslice_candidate_selection(
        selection_path,
        LambdaRemoteVSliceCandidateSelection(
            selection_status="requires_fresh_readonly_discovery",
            blockers=["fresh_readonly_discovery_required"],
        ),
    )

    decision = build_lambda_remote_vslice_retry_decision_from_path(
        candidate_selection=selection_path,
    )

    assert decision.decision_status == "wait_for_ssh_proven_candidate_live"
    assert decision.immediate_launch_authorized is False
    assert decision.launch_ready is False
    assert decision.launch_allowed is False


def test_retry_decision_can_authorize_future_review_for_selected_ssh_proven_pair(tmp_path):
    selection_path = tmp_path / "selection.json"
    write_lambda_remote_vslice_candidate_selection(
        selection_path,
        LambdaRemoteVSliceCandidateSelection(
            selection_status="selected_ssh_proven_candidate",
            selected_candidate="gpu_1x_a10",
            selected_region="us-east-1",
        ),
    )

    decision = build_lambda_remote_vslice_retry_decision_from_path(
        candidate_selection=selection_path,
    )

    assert decision.decision_status == "authorize_future_m067r2_on_ssh_proven_candidate"
    assert decision.selected_candidate == "gpu_1x_a10"
    assert decision.selected_region == "us-east-1"
