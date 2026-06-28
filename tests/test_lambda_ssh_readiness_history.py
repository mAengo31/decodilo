from __future__ import annotations

from lambda_m067s_helpers import write_ssh_history_reports

from decodilo.lambda_cloud.ssh_readiness_history import (
    build_lambda_ssh_readiness_history,
)


def test_ssh_readiness_history_detects_good_a10_and_bad_h100(tmp_path):
    paths = write_ssh_history_reports(tmp_path)

    history = build_lambda_ssh_readiness_history(report_paths=paths)

    assert history.ssh_ready_success_count == 5
    assert history.ssh_port_not_reachable_count == 1
    assert history.preferred_known_good_candidate_region == {
        "selected_candidate": "gpu_1x_a10",
        "selected_region": "us-east-1",
    }
    bad = [
        item
        for item in history.candidate_region_summaries
        if item.selected_candidate == "gpu_1x_h100_sxm5"
    ][0]
    assert bad.ssh_port_not_reachable_count == 1
    assert history.launch_ready is False
    assert history.launch_allowed is False
