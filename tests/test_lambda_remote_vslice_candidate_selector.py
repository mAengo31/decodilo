from __future__ import annotations

from lambda_m067s_helpers import (
    write_live_discovery,
    write_price_snapshot,
    write_ssh_history_reports,
)

from decodilo.lambda_cloud.remote_vslice_candidate_selector import (
    build_lambda_remote_vslice_candidate_selection_from_paths,
)
from decodilo.lambda_cloud.ssh_proven_candidate_policy import (
    build_lambda_ssh_proven_candidate_policy_from_path,
    write_lambda_ssh_proven_candidate_policy,
)
from decodilo.lambda_cloud.ssh_readiness_history import (
    build_lambda_ssh_readiness_history,
    write_lambda_ssh_readiness_history,
)


def _write_history_and_policy(tmp_path):
    history_path = tmp_path / "history.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_ssh_readiness_history(
        history_path,
        build_lambda_ssh_readiness_history(
            report_paths=write_ssh_history_reports(tmp_path)
        ),
    )
    write_lambda_ssh_proven_candidate_policy(
        policy_path,
        build_lambda_ssh_proven_candidate_policy_from_path(history=history_path),
    )
    return history_path, policy_path


def test_selector_requires_fresh_discovery_when_omitted(tmp_path):
    history, policy = _write_history_and_policy(tmp_path)

    selection = build_lambda_remote_vslice_candidate_selection_from_paths(
        ssh_readiness_history=history,
        ssh_proven_policy=policy,
        price_snapshot=write_price_snapshot(tmp_path),
    )

    assert selection.selection_status == "requires_fresh_readonly_discovery"
    assert selection.launch_ready is False
    assert selection.launch_allowed is False


def test_selector_prefers_live_ssh_proven_a10(tmp_path):
    history, policy = _write_history_and_policy(tmp_path)

    selection = build_lambda_remote_vslice_candidate_selection_from_paths(
        discovery_report=write_live_discovery(
            tmp_path,
            [("gpu_1x_a10", "us-east-1"), ("gpu_1x_h100_sxm5", "us-south-2")],
        ),
        ssh_readiness_history=history,
        ssh_proven_policy=policy,
        price_snapshot=write_price_snapshot(tmp_path),
    )

    assert selection.selection_status == "selected_ssh_proven_candidate"
    assert selection.selected_candidate == "gpu_1x_a10"
    assert selection.selected_region == "us-east-1"


def test_selector_does_not_silently_switch_to_unproven_candidate(tmp_path):
    history, policy = _write_history_and_policy(tmp_path)

    selection = build_lambda_remote_vslice_candidate_selection_from_paths(
        discovery_report=write_live_discovery(tmp_path, [("gpu_1x_h100_sxm5", "us-south-2")]),
        ssh_readiness_history=history,
        ssh_proven_policy=policy,
        price_snapshot=write_price_snapshot(tmp_path),
    )

    assert selection.selection_status == "known_ssh_ready_candidate_not_live"
    assert selection.selected_candidate is None
    assert "known_ssh_ready_candidate_not_live" in selection.blockers
