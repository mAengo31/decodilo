from __future__ import annotations

from lambda_m062_helpers import write_m062_chain

from decodilo.lambda_cloud.whoami_command_reconciliation import (
    build_lambda_whoami_command_reconciliation_from_paths,
)


def test_whoami_reconciliation_passes_clean_fixture(tmp_path):
    paths = write_m062_chain(tmp_path)

    reconciliation = build_lambda_whoami_command_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=paths["success"],
        final_discovery=paths["post_discovery"],
    )

    assert reconciliation.reconciliation_passed is True
    assert reconciliation.whoami_only_confirmed is True
    assert reconciliation.no_file_transfer_confirmed is True
    assert reconciliation.launch_ready is False
    assert reconciliation.launch_allowed is False


def test_whoami_reconciliation_blocks_visible_instance(tmp_path):
    paths = write_m062_chain(tmp_path, final_instance_count=1)

    reconciliation = build_lambda_whoami_command_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=paths["success"],
        final_discovery=paths["post_discovery"],
    )

    assert reconciliation.reconciliation_passed is False
    assert "final_discovery_visible_instances_present" in reconciliation.errors
