from lambda_m055d_helpers import write_m055d_base_inputs

from decodilo.lambda_cloud.ssh_capacity_retry_closeout import (
    build_lambda_ssh_capacity_retry_closeout_from_paths,
)


def test_ssh_capacity_retry_closeout_refines_teardown_review(tmp_path):
    paths = write_m055d_base_inputs(tmp_path)

    report = build_lambda_ssh_capacity_retry_closeout_from_paths(
        workdir=paths["workdir"],
        capacity_closeout=paths["capacity_closeout"],
        post_discovery=paths["post_discovery"],
    )

    assert report.closeout_status == "closed_capacity_unavailable_no_instance_created"
    assert report.teardown_review_status == "teardown_not_required_capacity_rejected"
    assert report.same_candidate_region_retry_blocked is True
    assert report.ssh_attempted is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
