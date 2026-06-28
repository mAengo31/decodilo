from __future__ import annotations

from lambda_m084_helpers import make_m083r_workdir, write_prior_ssh_history
from lambda_m088_helpers import make_m087r_workdir

from decodilo.lambda_cloud.ssh_proven_candidate_history_update import (
    build_lambda_ssh_proven_candidate_history_update_from_paths,
)


def test_ssh_history_update_records_us_west_1_without_overclaiming_others(tmp_path):
    workdir = make_m083r_workdir(tmp_path)
    prior = write_prior_ssh_history(tmp_path)

    report = build_lambda_ssh_proven_candidate_history_update_from_paths(
        prior_history=prior,
        workdir=workdir,
    )

    assert report.update_status == "ssh_proven_candidate_history_updated"
    assert report.gpu_1x_a10_us_west_1_recorded is True
    assert report.gpu_1x_a10_us_east_1_preserved is True
    assert report.unrelated_regions_not_marked_proven is True
    west = next(
        item
        for item in report.proven_candidate_regions
        if item["selected_region"] == "us-west-1"
    )
    assert all(west["proven_for"].values())
    h100 = [
        item
        for item in report.proven_candidate_regions
        if item["selected_candidate"] == "gpu_1x_h100_sxm5"
    ]
    assert h100 == []
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_history_update_records_m087r_parameter_fragment_evidence(tmp_path):
    workdir = make_m087r_workdir(tmp_path)
    prior = write_prior_ssh_history(tmp_path)

    report = build_lambda_ssh_proven_candidate_history_update_from_paths(
        prior_history=prior,
        workdir=workdir,
    )

    assert report.update_status == "ssh_proven_candidate_history_updated"
    assert report.milestone == "M088"
    assert report.gpu_1x_a10_us_west_1_recorded is True
    assert report.gpu_1x_a10_us_east_1_preserved is True
    west = next(
        item
        for item in report.proven_candidate_regions
        if item["selected_region"] == "us-west-1"
    )
    assert all(west["proven_for"].values())
    raw_m087r = next(
        item
        for item in report.candidate_region_records
        if item["milestone"] == "M087R"
    )
    assert raw_m087r["selected_region"] == "us-west-1"
    assert all(raw_m087r["proven_for"].values())
    assert report.launch_ready is False
    assert report.launch_allowed is False
