from __future__ import annotations

from lambda_m076_helpers import make_m075r4_workdir, write_m076_closeout_chain

from decodilo.lambda_cloud.runtime_smoke_artifact_audit import (
    build_lambda_runtime_smoke_artifact_audit_from_paths,
)


def test_runtime_smoke_artifact_audit_passes(tmp_path):
    workdir = make_m075r4_workdir(tmp_path)
    paths = write_m076_closeout_chain(tmp_path, workdir)

    audit = build_lambda_runtime_smoke_artifact_audit_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert audit.artifact_audit_passed is True
    assert audit.artifact_bytes == 1520
    assert audit.runtime_smoke_status == "passed"
    assert audit.protocol_or_event_check_passed is True
    assert audit.replay_or_metric_check_passed is True
    assert audit.launch_ready is False
    assert audit.launch_allowed is False
