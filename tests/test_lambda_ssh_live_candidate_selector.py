from lambda_m055d_helpers import write_m055d_base_inputs

from decodilo.lambda_cloud.ssh_capacity_history import (
    build_lambda_ssh_capacity_history_from_paths,
    write_lambda_ssh_capacity_history,
)
from decodilo.lambda_cloud.ssh_capacity_retry_closeout import (
    build_lambda_ssh_capacity_retry_closeout_from_paths,
    write_lambda_ssh_capacity_retry_closeout,
)
from decodilo.lambda_cloud.ssh_live_candidate_selector import (
    build_lambda_ssh_live_candidate_selection_from_paths,
)


def test_live_candidate_selector_picks_cheapest_live_a10(tmp_path):
    paths = write_m055d_base_inputs(tmp_path)
    closeout = tmp_path / "ssh-closeout.json"
    history = tmp_path / "history.json"
    write_lambda_ssh_capacity_retry_closeout(
        closeout,
        build_lambda_ssh_capacity_retry_closeout_from_paths(
            workdir=paths["workdir"],
            capacity_closeout=paths["capacity_closeout"],
            post_discovery=paths["post_discovery"],
        ),
    )
    write_lambda_ssh_capacity_history(
        history,
        build_lambda_ssh_capacity_history_from_paths(
            latest_closeout=closeout,
            prior_m055b_report=tmp_path / "missing.json",
        ),
    )

    report = build_lambda_ssh_live_candidate_selection_from_paths(
        discovery_report=paths["live_discovery"],
        price_snapshot=paths["price_snapshot"],
        ssh_key_selection=paths["ssh_selection"],
        capacity_history=history,
        max_budget=50,
    )

    assert report.selection_status == "selected_live_candidate"
    assert report.selected_candidate == "gpu_1x_a10"
    assert report.selected_region == "us-east-1"
    assert report.selected_candidate_source == "live_readonly_instance_types"
    assert report.buffered_estimated_30min_cost == 1.29 * 0.5 * 1.15
    assert report.launch_ready is False
    assert report.launch_allowed is False
