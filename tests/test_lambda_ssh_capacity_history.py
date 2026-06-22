from lambda_m055d_helpers import write_m055d_base_inputs

from decodilo.lambda_cloud.ssh_capacity_history import (
    build_lambda_ssh_capacity_history_from_paths,
)
from decodilo.lambda_cloud.ssh_capacity_retry_closeout import (
    build_lambda_ssh_capacity_retry_closeout_from_paths,
    write_lambda_ssh_capacity_retry_closeout,
)


def test_ssh_capacity_history_records_capacity_rejection(tmp_path):
    paths = write_m055d_base_inputs(tmp_path)
    closeout_path = tmp_path / "ssh-closeout.json"
    write_lambda_ssh_capacity_retry_closeout(
        closeout_path,
        build_lambda_ssh_capacity_retry_closeout_from_paths(
            workdir=paths["workdir"],
            capacity_closeout=paths["capacity_closeout"],
            post_discovery=paths["post_discovery"],
        ),
    )

    report = build_lambda_ssh_capacity_history_from_paths(
        latest_closeout=closeout_path,
        prior_m055b_report=tmp_path / "missing.json",
    )

    assert report.capacity_rejections_count == 1
    assert "gpu_8x_a100_80gb_sxm4/us-midwest-1" in (
        report.candidates_with_capacity_rejection
    )
    assert report.retry_same_candidate_region_recommended is False
    assert report.launch_ready is False
