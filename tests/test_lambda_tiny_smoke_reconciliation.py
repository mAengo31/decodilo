from lambda_m074_helpers import make_m073r2_workdir

from decodilo.lambda_cloud.tiny_smoke_reconciliation import (
    build_lambda_tiny_smoke_reconciliation_from_paths,
)
from decodilo.lambda_cloud.tiny_smoke_success_record import (
    build_lambda_tiny_smoke_success_record_from_paths,
    write_lambda_tiny_smoke_success_record,
)


def test_tiny_smoke_reconciliation_passes_for_clean_closeout(tmp_path):
    workdir = make_m073r2_workdir(tmp_path)
    record_path = tmp_path / "success.json"
    write_lambda_tiny_smoke_success_record(
        record_path,
        build_lambda_tiny_smoke_success_record_from_paths(workdir=workdir),
    )

    reconciliation = build_lambda_tiny_smoke_reconciliation_from_paths(
        workdir=workdir,
        success_record=record_path,
    )

    assert reconciliation.reconciliation_passed is True
    assert reconciliation.no_unapproved_file_transfer is True
    assert reconciliation.no_training is True
    assert reconciliation.no_downloads is True
    assert reconciliation.no_internet_install is True
    assert reconciliation.launch_ready is False
    assert reconciliation.launch_allowed is False
