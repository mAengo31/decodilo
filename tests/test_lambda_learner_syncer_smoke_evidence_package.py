from __future__ import annotations

from lambda_m080_helpers import make_m079r2_workdir, write_m080_closeout_chain

from decodilo.lambda_cloud.learner_syncer_smoke_evidence_package import (
    build_lambda_learner_syncer_smoke_evidence_package_from_paths,
)


def test_learner_syncer_evidence_package_complete_for_success(tmp_path):
    workdir = make_m079r2_workdir(tmp_path)
    paths = write_m080_closeout_chain(tmp_path, workdir)

    package = build_lambda_learner_syncer_smoke_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert package.evidence_complete is True
    assert package.learner_syncer_smoke_success is True
    assert package.reconciliation_passed is True
    assert package.launch_ready is False
    assert package.launch_allowed is False
