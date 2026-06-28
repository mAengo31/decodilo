from __future__ import annotations

from lambda_m067s_helpers import write_ssh_history_reports

from decodilo.lambda_cloud.ssh_proven_candidate_policy import (
    build_lambda_ssh_proven_candidate_policy_from_path,
)
from decodilo.lambda_cloud.ssh_readiness_history import (
    build_lambda_ssh_readiness_history,
    write_lambda_ssh_readiness_history,
)


def test_ssh_proven_policy_excludes_recent_port_failure(tmp_path):
    history_path = tmp_path / "history.json"
    write_lambda_ssh_readiness_history(
        history_path,
        build_lambda_ssh_readiness_history(
            report_paths=write_ssh_history_reports(tmp_path)
        ),
    )

    policy = build_lambda_ssh_proven_candidate_policy_from_path(history=history_path)

    assert policy.preferred_known_good_candidate_region == {
        "selected_candidate": "gpu_1x_a10",
        "selected_region": "us-east-1",
    }
    assert any(
        item["selected_candidate"] == "gpu_1x_h100_sxm5"
        and item["selected_region"] == "us-south-2"
        for item in policy.excluded_candidate_regions
    )
    assert policy.silent_unproven_substitution_allowed is False
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
