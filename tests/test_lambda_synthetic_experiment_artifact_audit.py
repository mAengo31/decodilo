from __future__ import annotations

from lambda_m078_helpers import make_m077r_workdir, write_m078_closeout_chain

from decodilo.lambda_cloud.synthetic_experiment_artifact_audit import (
    build_lambda_synthetic_experiment_artifact_audit_from_paths,
)


def test_synthetic_experiment_artifact_audit_passes(tmp_path):
    workdir = make_m077r_workdir(tmp_path)
    paths = write_m078_closeout_chain(tmp_path, workdir)

    audit = build_lambda_synthetic_experiment_artifact_audit_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert audit.artifact_audit_passed is True
    assert audit.artifact_bytes == 1909
    assert audit.synthetic_experiment_status == "passed"
    assert audit.learner_or_runtime_check_passed is True
    assert audit.update_or_commit_check_passed is True
    assert audit.replay_or_metric_check_passed is True
    assert audit.launch_ready is False
    assert audit.launch_allowed is False
