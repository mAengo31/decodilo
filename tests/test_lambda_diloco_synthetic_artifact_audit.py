from __future__ import annotations

from lambda_m082_helpers import make_m081r2_workdir, write_m082_closeout_chain

from decodilo.lambda_cloud.diloco_synthetic_artifact_audit import (
    build_lambda_diloco_synthetic_artifact_audit_from_paths,
)


def test_diloco_synthetic_artifact_audit_passes_and_preserves_fidelity(tmp_path):
    workdir = make_m081r2_workdir(tmp_path)
    paths = write_m082_closeout_chain(tmp_path, workdir)

    audit = build_lambda_diloco_synthetic_artifact_audit_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert audit.artifact_audit_passed is True
    assert audit.artifact_bytes == 3355
    assert audit.artifact_sha256 == (
        "7e42f2058879dc07853f53c77ffc6729a4c0e9cab23b3b9652c07abb63efce53"
    )
    assert audit.optimization_fidelity == "diloco_shaped_protocol_only"
    assert audit.inner_optimizer_semantics == "synthetic_placeholder"
    assert audit.outer_optimizer_semantics == "token_weighted_merge"
    assert audit.parameter_fragment_semantics == "not_exercised"
    assert audit.launch_ready is False
    assert audit.launch_allowed is False
