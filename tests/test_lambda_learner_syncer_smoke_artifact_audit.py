from __future__ import annotations

from lambda_m080_helpers import make_m079r2_workdir, write_m080_closeout_chain

from decodilo.lambda_cloud.learner_syncer_smoke_artifact_audit import (
    build_lambda_learner_syncer_smoke_artifact_audit_from_paths,
)
from decodilo.lambda_cloud.learner_syncer_smoke_success_record import (
    M079R2_LEARNER_SYNCER_ARTIFACT_SHA256,
)


def test_learner_syncer_artifact_audit_passes_for_persisted_safe_body(tmp_path):
    workdir = make_m079r2_workdir(tmp_path)
    paths = write_m080_closeout_chain(tmp_path, workdir)

    audit = build_lambda_learner_syncer_smoke_artifact_audit_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert audit.artifact_audit_passed is True
    assert audit.artifact_sha256 == M079R2_LEARNER_SYNCER_ARTIFACT_SHA256
    assert audit.safe_json_body_persisted is True
    assert audit.parsed_summary_persisted is True
    assert audit.learner_syncer_smoke_status == "passed"
    assert audit.launch_ready is False
    assert audit.launch_allowed is False
