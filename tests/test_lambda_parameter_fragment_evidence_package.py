from __future__ import annotations

from lambda_m088_helpers import make_m087r_workdir, write_m088_parameter_fragment_closeout_chain

from decodilo.lambda_cloud.parameter_fragment_evidence_package import (
    build_lambda_parameter_fragment_evidence_package_from_paths,
)


def test_parameter_fragment_evidence_package_is_complete(tmp_path):
    paths = write_m088_parameter_fragment_closeout_chain(
        tmp_path,
        make_m087r_workdir(tmp_path),
    )

    report = build_lambda_parameter_fragment_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert report.evidence_complete is True
    assert report.parameter_fragment_success is True
    assert report.reconciliation_passed is True
    assert report.fragment_semantics_confirmed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
