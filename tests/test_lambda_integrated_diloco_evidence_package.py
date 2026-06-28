from __future__ import annotations

from lambda_m086_helpers import make_m085r_workdir, write_m086_integrated_closeout_chain

from decodilo.lambda_cloud.integrated_diloco_evidence_package import (
    load_lambda_integrated_diloco_evidence_package,
)


def test_integrated_diloco_evidence_package_is_complete(tmp_path):
    paths = write_m086_integrated_closeout_chain(
        tmp_path,
        make_m085r_workdir(tmp_path),
    )

    package = load_lambda_integrated_diloco_evidence_package(paths["evidence"])

    assert package.evidence_complete is True
    assert package.integrated_diloco_success is True
    assert package.integrated_semantics_confirmed is True
    assert package.launch_ready is False
    assert package.launch_allowed is False
