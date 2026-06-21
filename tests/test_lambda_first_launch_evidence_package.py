from lambda_m023_helpers import (
    build_m023_evidence_package_from_refs,
    write_m023_core_artifacts,
)


def test_evidence_package_builds_from_complete_fake_artifacts(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)

    package = build_m023_evidence_package_from_refs(refs)

    assert package.evidence_complete is True
    assert package.future_real_launch_review_candidate is True
    assert package.real_mutation_enabled is False
    assert package.launch_allowed is False


def test_evidence_package_blocks_missing_discovery(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)

    package = build_m023_evidence_package_from_refs(
        refs,
        m019c_discovery=tmp_path / "missing.json",
    )

    assert package.evidence_complete is False
    assert "m019c_discovery" in package.missing_items
    assert any("missing evidence" in blocker for blocker in package.blockers)


def test_evidence_package_detects_hash_mismatch(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)

    package = build_m023_evidence_package_from_refs(
        refs,
        expected_hashes={"m019c_discovery": "bad"},
    )

    assert "m019c_discovery" in package.hash_mismatches
    assert any("hash mismatch" in blocker for blocker in package.blockers)
