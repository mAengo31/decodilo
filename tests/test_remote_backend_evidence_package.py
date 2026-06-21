from pathlib import Path

from decodilo.storage.remote_backend_evidence import (
    build_remote_backend_evidence_package,
    validate_remote_backend_evidence_package,
    write_remote_backend_evidence_package,
)


def test_evidence_package_hashes_and_serializes(tmp_path: Path) -> None:
    scaling = tmp_path / "scaling.json"
    requirements = tmp_path / "requirements.json"
    scaling.write_text('{"kind":"scaling"}\n', encoding="utf-8")
    requirements.write_text('{"kind":"requirements"}\n', encoding="utf-8")

    package = build_remote_backend_evidence_package(
        evidence_paths={
            "learner_scaling_report": scaling,
            "remote_requirements": requirements,
        }
    )

    assert package.manifest.evidence_completeness_score == 1.0
    assert all(item.sha256 for item in package.manifest.items)
    path = tmp_path / "evidence.json"
    write_remote_backend_evidence_package(path, package)
    assert path.exists()
    assert package.remote_backend_enabled is False
    assert package.launch_allowed is False


def test_missing_item_lowers_completeness_and_hash_mismatch_detected(tmp_path: Path) -> None:
    scaling = tmp_path / "scaling.json"
    scaling.write_text('{"kind":"scaling"}\n', encoding="utf-8")
    package = build_remote_backend_evidence_package(
        evidence_paths={
            "learner_scaling_report": scaling,
            "remote_requirements": tmp_path / "missing.json",
        }
    )

    assert package.manifest.evidence_completeness_score == 0.5
    assert "remote_requirements" in package.manifest.missing_required_items

    scaling.write_text('{"kind":"tampered"}\n', encoding="utf-8")
    validation = validate_remote_backend_evidence_package(package)
    assert "learner_scaling_report" in validation.hash_errors
