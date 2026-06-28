from __future__ import annotations

from lambda_m076_helpers import make_m075r4_workdir, write_m076_closeout_chain

from decodilo.lambda_cloud.runtime_smoke_closeout import (
    build_lambda_runtime_smoke_closeout_from_paths,
)


def test_runtime_smoke_closeout_succeeds(tmp_path):
    workdir = make_m075r4_workdir(tmp_path)
    paths = write_m076_closeout_chain(tmp_path, workdir)

    closeout = build_lambda_runtime_smoke_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status in {"closed_success", "closed_with_warnings"}
    assert closeout.runtime_smoke_success is True
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
