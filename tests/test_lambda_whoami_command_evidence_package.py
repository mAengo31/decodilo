from __future__ import annotations

from lambda_m062_helpers import write_m062_chain

from decodilo.lambda_cloud.whoami_command_evidence_package import (
    build_lambda_whoami_command_evidence_package_from_paths,
)


def test_whoami_evidence_package_complete(tmp_path):
    paths = write_m062_chain(tmp_path)

    evidence = build_lambda_whoami_command_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert evidence.evidence_complete is True
    assert evidence.whoami_command_success is True
    assert "journal" in evidence.evidence_refs
    assert evidence.launch_ready is False
    assert evidence.launch_allowed is False


def test_whoami_evidence_package_blocks_missing_journal(tmp_path):
    paths = write_m062_chain(tmp_path)
    (paths["workdir"] / "journal.jsonl").unlink()

    evidence = build_lambda_whoami_command_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert evidence.evidence_complete is False
    assert "missing_evidence:journal" in evidence.blockers
