from decodilo.storage.remote_backend_evidence_review import review_evidence_hashes


def test_evidence_review_detects_missing_and_hash_mismatch(tmp_path) -> None:
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"ok":true}\n', encoding="utf-8")

    report = review_evidence_hashes(
        expected_hashes={
            str(artifact): "not-the-hash",
            str(tmp_path / "missing.json"): "abc",
        }
    )

    assert report.passed is False
    assert str(artifact) in report.hash_mismatches
    assert str(tmp_path / "missing.json") in report.missing_references
