import hashlib

from lambda_m025_helpers import write_m025_core_artifacts

from decodilo.lambda_cloud.final_prelaunch_evidence_package import (
    build_lambda_final_prelaunch_evidence_package,
)


def test_complete_final_prelaunch_evidence_package_builds(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    package = build_lambda_final_prelaunch_evidence_package(
        m019c_discovery=paths["discovery"],
        m019c_audit=paths["audit"],
        m020_report=paths["m020"],
        m022_readiness_package=paths["readiness"],
        m023_evidence_package=paths["m023_package"],
        m024_skeleton_audit=paths["skeleton"],
    )

    assert package.evidence_complete is True
    assert package.future_first_launch_candidate is True
    assert package.launch_allowed is False


def test_missing_m019c_discovery_blocks(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    package = build_lambda_final_prelaunch_evidence_package(
        m019c_discovery=tmp_path / "missing.json",
        m019c_audit=paths["audit"],
        m020_report=paths["m020"],
        m022_readiness_package=paths["readiness"],
        m023_evidence_package=paths["m023_package"],
        m024_skeleton_audit=paths["skeleton"],
    )

    assert "m019c_discovery" in package.missing_items
    assert package.evidence_complete is False


def test_hash_mismatch_blocks(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    digest = hashlib.sha256(paths["discovery"].read_bytes()).hexdigest()
    package = build_lambda_final_prelaunch_evidence_package(
        m019c_discovery=paths["discovery"],
        m019c_audit=paths["audit"],
        m020_report=paths["m020"],
        m022_readiness_package=paths["readiness"],
        m023_evidence_package=paths["m023_package"],
        m024_skeleton_audit=paths["skeleton"],
        expected_hashes={"m019c_discovery": "bad" + digest[3:]},
    )

    assert package.hash_mismatches == ["m019c_discovery"]
    assert package.launch_ready is False
