from __future__ import annotations

from lambda_m067s_helpers import write_m067r_artifacts

from decodilo.lambda_cloud.remote_vertical_slice_closeout import (
    build_lambda_remote_vertical_slice_closeout_from_paths,
    write_lambda_remote_vertical_slice_closeout,
)
from decodilo.lambda_cloud.remote_vertical_slice_reconciliation import (
    build_lambda_remote_vertical_slice_reconciliation_from_paths,
)


def test_m067r_reconciliation_passes_with_no_upload_or_remote_command(tmp_path):
    paths = write_m067r_artifacts(tmp_path)
    closeout_path = tmp_path / "closeout.json"
    write_lambda_remote_vertical_slice_closeout(
        closeout_path,
        build_lambda_remote_vertical_slice_closeout_from_paths(
            workdir=paths["workdir"],
            evidence=paths["evidence"],
            post_discovery=paths["post"],
        ),
    )

    reconciliation = build_lambda_remote_vertical_slice_reconciliation_from_paths(
        workdir=paths["workdir"],
        closeout=closeout_path,
    )

    assert reconciliation.reconciliation_passed is True
    assert reconciliation.owned_instance_final_state == "absent"
    assert reconciliation.bundle_upload_attempted is False
    assert reconciliation.remote_command_attempted is False
    assert reconciliation.launch_ready is False
    assert reconciliation.launch_allowed is False
