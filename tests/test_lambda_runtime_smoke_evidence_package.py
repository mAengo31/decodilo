from __future__ import annotations

from lambda_m076_helpers import make_m075r4_workdir, write_m076_closeout_chain

from decodilo.lambda_cloud.runtime_smoke_evidence_package import (
    build_lambda_runtime_smoke_evidence_package_from_paths,
)


def test_runtime_smoke_evidence_package_is_complete(tmp_path):
    workdir = make_m075r4_workdir(tmp_path)
    paths = write_m076_closeout_chain(tmp_path, workdir)

    package = build_lambda_runtime_smoke_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert package.evidence_complete is True
    assert package.runtime_smoke_success is True
    assert package.reconciliation_passed is True
    assert package.launch_ready is False
    assert package.launch_allowed is False
