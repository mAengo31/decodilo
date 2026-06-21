from __future__ import annotations

from lambda_m047_helpers import write_m046c_workdir

from decodilo.lambda_cloud.lifecycle_smoke_evidence_package import (
    build_lambda_lifecycle_smoke_evidence_package_from_paths,
)
from decodilo.lambda_cloud.lifecycle_smoke_postrun_reconciliation import (
    build_lambda_lifecycle_smoke_postrun_reconciliation_from_paths,
    write_lambda_lifecycle_smoke_postrun_reconciliation,
)
from decodilo.lambda_cloud.lifecycle_smoke_success_record import (
    build_lambda_lifecycle_smoke_success_record_from_paths,
    write_lambda_lifecycle_smoke_success_record,
)


def _write_success_and_reconciliation(tmp_path):
    paths = write_m046c_workdir(tmp_path)
    paths["success"] = tmp_path / "success.json"
    paths["reconciliation"] = tmp_path / "reconciliation.json"
    success = build_lambda_lifecycle_smoke_success_record_from_paths(
        workdir=paths["workdir"],
        final_summary=paths["final_summary"],
        post_discovery=paths["post_discovery"],
    )
    write_lambda_lifecycle_smoke_success_record(paths["success"], success)
    reconciliation = build_lambda_lifecycle_smoke_postrun_reconciliation_from_paths(
        workdir=paths["workdir"],
        post_discovery=paths["post_discovery"],
    )
    write_lambda_lifecycle_smoke_postrun_reconciliation(
        paths["reconciliation"],
        reconciliation,
    )
    return paths


def test_complete_evidence_package_passes(tmp_path):
    paths = _write_success_and_reconciliation(tmp_path)

    package = build_lambda_lifecycle_smoke_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert package.evidence_complete is True
    assert package.lifecycle_smoke_success is True
    assert package.missing_items == []
    assert package.launch_ready is False
    assert package.launch_allowed is False


def test_missing_journal_blocks_evidence_package(tmp_path):
    paths = _write_success_and_reconciliation(tmp_path)
    (paths["workdir"] / "journal.jsonl").unlink()

    package = build_lambda_lifecycle_smoke_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert package.evidence_complete is False
    assert "journal" in package.missing_items
