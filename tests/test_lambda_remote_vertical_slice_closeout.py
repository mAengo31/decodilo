from __future__ import annotations

from lambda_m067s_helpers import write_m067r_artifacts

from decodilo.lambda_cloud.remote_vertical_slice_closeout import (
    build_lambda_remote_vertical_slice_closeout_from_paths,
)


def test_m067r_closes_as_pre_manifest_ssh_port_not_reachable(tmp_path):
    paths = write_m067r_artifacts(tmp_path)

    closeout = build_lambda_remote_vertical_slice_closeout_from_paths(
        workdir=paths["workdir"],
        evidence=paths["evidence"],
        post_discovery=paths["post"],
    )

    assert closeout.closeout_status == "closed_pre_manifest_ssh_port_not_reachable"
    assert closeout.failed_stage == "ssh_port_not_reachable"
    assert closeout.decodilo_not_tested is True
    assert closeout.source_bundle_upload_attempted is False
    assert closeout.manifest_started is False
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
