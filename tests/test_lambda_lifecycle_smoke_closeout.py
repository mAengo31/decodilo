from __future__ import annotations

from lambda_m047_helpers import write_m047_inputs

from decodilo.lambda_cloud.lifecycle_smoke_closeout import (
    build_lambda_lifecycle_smoke_closeout_from_paths,
)


def test_clean_lifecycle_smoke_closeout_succeeds(tmp_path):
    paths = write_m047_inputs(tmp_path)

    closeout = build_lambda_lifecycle_smoke_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status in {"closed_success", "closed_with_warnings"}
    assert closeout.final_instance_count == 0
    assert closeout.final_unmanaged_count == 0
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
