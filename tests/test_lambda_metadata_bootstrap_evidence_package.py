from __future__ import annotations

from lambda_m052_helpers import write_m052_inputs

from decodilo.lambda_cloud.metadata_bootstrap_evidence_package import (
    build_lambda_metadata_bootstrap_evidence_package_from_paths,
)


def test_complete_metadata_evidence_package_passes(tmp_path):
    paths = write_m052_inputs(tmp_path)

    package = build_lambda_metadata_bootstrap_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        metadata_plan=paths["workdir"] / "report.json",
        execution_gate=paths["workdir"] / "report.json",
        no_mutation_no_ssh_audit=paths["workdir"] / "report.json",
        reviewer_bridge=paths["workdir"] / "report.json",
        arming_gate=paths["workdir"] / "report.json",
        m050_report=paths["workdir"] / "report.json",
    )

    assert package.evidence_complete is True
    assert package.metadata_bootstrap_success is True
    assert package.launch_ready is False
    assert package.launch_allowed is False


def test_missing_journal_blocks_metadata_evidence_package(tmp_path):
    paths = write_m052_inputs(tmp_path)
    (paths["workdir"] / "journal.jsonl").unlink()

    package = build_lambda_metadata_bootstrap_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        metadata_plan=paths["workdir"] / "report.json",
        execution_gate=paths["workdir"] / "report.json",
        no_mutation_no_ssh_audit=paths["workdir"] / "report.json",
        reviewer_bridge=paths["workdir"] / "report.json",
        arming_gate=paths["workdir"] / "report.json",
        m050_report=paths["workdir"] / "report.json",
    )

    assert package.evidence_complete is False
    assert "journal" in package.missing_items


def test_hash_mismatch_blocks_metadata_evidence_package(tmp_path):
    paths = write_m052_inputs(tmp_path)

    package = build_lambda_metadata_bootstrap_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        expected_hashes={"success_record": "not-the-real-hash"},
        metadata_plan=paths["workdir"] / "report.json",
        execution_gate=paths["workdir"] / "report.json",
        no_mutation_no_ssh_audit=paths["workdir"] / "report.json",
        reviewer_bridge=paths["workdir"] / "report.json",
        arming_gate=paths["workdir"] / "report.json",
        m050_report=paths["workdir"] / "report.json",
    )

    assert package.evidence_complete is False
    assert "success_record" in package.hash_mismatches
