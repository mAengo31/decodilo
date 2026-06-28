from __future__ import annotations

from lambda_m062_helpers import write_m062_chain

from decodilo.lambda_cloud.whoami_command_closeout import (
    build_lambda_whoami_command_closeout_from_paths,
)


def test_whoami_closeout_succeeds_for_clean_chain(tmp_path):
    paths = write_m062_chain(tmp_path)

    closeout = build_lambda_whoami_command_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status == "closed_with_warnings"
    assert closeout.command == "whoami"
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
