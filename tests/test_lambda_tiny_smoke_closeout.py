from lambda_m074_helpers import make_m073r2_workdir

from decodilo.lambda_cloud.tiny_smoke_closeout import (
    build_lambda_tiny_smoke_closeout_from_paths,
)
from decodilo.lambda_cloud.tiny_smoke_evidence_package import (
    build_lambda_tiny_smoke_evidence_package_from_paths,
    write_lambda_tiny_smoke_evidence_package,
)
from decodilo.lambda_cloud.tiny_smoke_reconciliation import (
    build_lambda_tiny_smoke_reconciliation_from_paths,
    write_lambda_tiny_smoke_reconciliation,
)
from decodilo.lambda_cloud.tiny_smoke_success_record import (
    build_lambda_tiny_smoke_success_record_from_paths,
    write_lambda_tiny_smoke_success_record,
)


def test_tiny_smoke_closeout_succeeds_with_warnings_for_historical_billable(tmp_path):
    workdir = make_m073r2_workdir(tmp_path)
    success_path = tmp_path / "success.json"
    reconciliation_path = tmp_path / "reconciliation.json"
    evidence_path = tmp_path / "evidence.json"
    write_lambda_tiny_smoke_success_record(
        success_path,
        build_lambda_tiny_smoke_success_record_from_paths(workdir=workdir),
    )
    write_lambda_tiny_smoke_reconciliation(
        reconciliation_path,
        build_lambda_tiny_smoke_reconciliation_from_paths(
            workdir=workdir,
            success_record=success_path,
        ),
    )
    write_lambda_tiny_smoke_evidence_package(
        evidence_path,
        build_lambda_tiny_smoke_evidence_package_from_paths(
            success_record=success_path,
            reconciliation=reconciliation_path,
        ),
    )

    closeout = build_lambda_tiny_smoke_closeout_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        evidence_package=evidence_path,
    )

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status == "closed_with_warnings"
    assert closeout.historical_billable_action_performed is True
    assert closeout.billable_action_performed is False
