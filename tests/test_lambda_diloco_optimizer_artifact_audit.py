from __future__ import annotations

from lambda_m084_helpers import make_m083r_workdir, write_m084_optimizer_closeout_chain

from decodilo.lambda_cloud.diloco_optimizer_artifact_audit import (
    build_lambda_diloco_optimizer_artifact_audit_from_paths,
)
from decodilo.lambda_cloud.diloco_optimizer_success_record import (
    M083R_OPTIMIZER_ARTIFACT_SHA256,
)


def test_diloco_optimizer_artifact_audit_preserves_semantics(tmp_path):
    workdir = make_m083r_workdir(tmp_path)
    paths = write_m084_optimizer_closeout_chain(tmp_path, workdir)

    report = build_lambda_diloco_optimizer_artifact_audit_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert report.artifact_audit_passed is True
    assert report.artifact_sha256 == M083R_OPTIMIZER_ARTIFACT_SHA256
    assert report.diloco_optimizer_smoke_status == "passed"
    assert report.optimization_fidelity == "optimizer_semantics_smoke"
    assert report.inner_optimizer_semantics == "adamw"
    assert report.outer_optimizer_semantics == "nesterov"
    assert report.parameter_fragment_semantics == "not_exercised"
    assert report.max_abs_error == 0.0
    assert report.launch_ready is False
    assert report.launch_allowed is False
