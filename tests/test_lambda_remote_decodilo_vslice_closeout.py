from __future__ import annotations

from lambda_m070_helpers import make_m069r_workdir

from decodilo.lambda_cloud.remote_decodilo_vslice_closeout import (
    build_lambda_remote_decodilo_vslice_closeout_from_paths,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_evidence_package import (
    build_lambda_remote_decodilo_vslice_evidence_package_from_paths,
    write_lambda_remote_decodilo_vslice_evidence_package,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_reconciliation import (
    build_lambda_remote_decodilo_vslice_reconciliation_from_paths,
    write_lambda_remote_decodilo_vslice_reconciliation,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_success_record import (
    build_lambda_remote_decodilo_vslice_success_record_from_paths,
    write_lambda_remote_decodilo_vslice_success_record,
)


def test_remote_decodilo_closeout_succeeds(tmp_path):
    workdir = make_m069r_workdir(tmp_path)
    success_path = tmp_path / "success.json"
    reconciliation_path = tmp_path / "reconciliation.json"
    evidence_path = tmp_path / "evidence.json"
    write_lambda_remote_decodilo_vslice_success_record(
        success_path,
        build_lambda_remote_decodilo_vslice_success_record_from_paths(workdir=workdir),
    )
    write_lambda_remote_decodilo_vslice_reconciliation(
        reconciliation_path,
        build_lambda_remote_decodilo_vslice_reconciliation_from_paths(
            workdir=workdir,
            success_record=success_path,
        ),
    )
    write_lambda_remote_decodilo_vslice_evidence_package(
        evidence_path,
        build_lambda_remote_decodilo_vslice_evidence_package_from_paths(
            success_record=success_path,
            reconciliation=reconciliation_path,
        ),
    )

    closeout = build_lambda_remote_decodilo_vslice_closeout_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        evidence_package=evidence_path,
    )

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status in {"closed_success", "closed_with_warnings"}
    assert closeout.billable_action_performed is False
