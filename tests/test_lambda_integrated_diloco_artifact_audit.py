from __future__ import annotations

from lambda_m086_helpers import make_m085r_workdir, write_m086_integrated_closeout_chain

from decodilo.lambda_cloud.integrated_diloco_artifact_audit import (
    build_lambda_integrated_diloco_artifact_audit_from_paths,
)
from decodilo.lambda_cloud.integrated_diloco_success_record import (
    M085R_INTEGRATED_ARTIFACT_SHA256,
)


def test_integrated_diloco_artifact_audit_preserves_claim_boundaries(tmp_path):
    workdir = make_m085r_workdir(tmp_path)
    paths = write_m086_integrated_closeout_chain(tmp_path, workdir)

    report = build_lambda_integrated_diloco_artifact_audit_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert report.artifact_audit_passed is True
    assert report.artifact_sha256 == M085R_INTEGRATED_ARTIFACT_SHA256
    assert report.optimization_fidelity == "integrated_optimizer_protocol_smoke"
    assert report.parameter_fragment_semantics == "not_exercised"
    assert report.protocol_optimizer_link_check_passed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
